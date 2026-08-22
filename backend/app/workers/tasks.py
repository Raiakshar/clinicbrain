import asyncio
from datetime import UTC, date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models import Clinic, Document, Patient, TimelineEvent, WhatsAppLog
from app.services.storage import get_storage
from app.workers.celery_app import celery_app


def get_session_maker() -> tuple[async_sessionmaker, AsyncEngine]:
    from app.db import worker_session_maker

    return worker_session_maker()


def _provider():
    from app.config import settings

    if settings.extraction_provider == "fake":
        from app.services.extraction.fake import FakeProvider

        return FakeProvider()
    from app.services.extraction.gpt import GPTProvider

    return GPTProvider()


async def _run(document_id: int, mode: str) -> None:
    maker, eng = get_session_maker()
    try:
        async with maker() as db:
            doc = (await db.scalars(select(Document).where(Document.id == document_id))).first()
            if not doc or doc.status != ("pending" if mode == "full" else "needs_review"):
                return
            if mode == "full":
                await _extract_doc(db, doc)
            else:
                await _extract_lab_rows(db, doc)
    finally:
        await eng.dispose()


async def _extract_doc(db, doc: Document) -> None:
    doc.status = "processing"
    await db.commit()
    try:
        data = get_storage().get(doc.s3_key)
        provider = _provider()
        result = await provider.extract(data, doc.mime)
        doc.ocr_text = result.content_text
        extracted = result.model_dump(mode="json")
        if result.document_type == "lab":
            try:
                labs = await provider.extract_labs(data, doc.mime)
                extracted["labs"] = [r.model_dump(mode="json") for r in labs.rows]
            except Exception as e:
                extracted["labs"] = []
                extracted["lab_error"] = str(e)[:300]
        doc.extracted = extracted
        doc.status = "needs_review"
        doc.error = None
    except Exception as e:
        doc.status = "failed"
        doc.error = str(e)[:800]
    await db.commit()


async def _extract_lab_rows(db, doc: Document) -> None:
    try:
        data = get_storage().get(doc.s3_key)
        labs = await _provider().extract_labs(data, doc.mime)
        extracted = dict(doc.extracted or {})
        extracted["labs"] = [r.model_dump(mode="json") for r in labs.rows]
        extracted.pop("lab_error", None)
        doc.extracted = extracted
    except Exception as e:
        extracted = dict(doc.extracted or {})
        extracted["labs"] = []
        extracted["lab_error"] = str(e)[:300]
        doc.extracted = extracted
    await db.commit()


@celery_app.task(name="documents.extract")
def extract_document_task(document_id: str) -> None:
    asyncio.run(_run(int(document_id), "full"))


@celery_app.task(name="documents.extract_labs")
def extract_labs_task(document_id: str) -> None:
    asyncio.run(_run(int(document_id), "labs"))


async def _enqueue_whatsapp(
    db, patient_id: int, template: str, body: str
) -> int | None:
    patient = await db.get(Patient, patient_id)
    if not patient or patient.whatsapp_consent is False or not patient.phone:
        return None
    log = WhatsAppLog(patient_id=patient_id, template=template, body=body, status="retrying")
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log.id


@celery_app.task(
    name="whatsapp.send",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=False,
    max_retries=3,
)
def send_whatsapp_task(self, log_id: str) -> None:
    asyncio.run(_send_whatsapp(int(log_id), self.request.retries))


async def _send_whatsapp(log_id: int, attempt: int) -> None:
    from app.services.whatsapp import WhatsAppError, get_whatsapp_provider

    maker, eng = get_session_maker()
    try:
        async with maker() as db:
            log = await db.get(WhatsAppLog, log_id)
            if not log or log.status == "sent":
                return
            patient = await db.get(Patient, log.patient_id)
            try:
                await get_whatsapp_provider().send(str(patient.phone), log.body or "")
                log.status = "sent"
                log.sent_at = func_now()
                log.error = None
                await db.commit()
            except WhatsAppError as e:
                log.retries = attempt + 1
                log.error = str(e)[:500]
                if attempt >= 3:
                    log.status = "failed"
                    await db.commit()
                    return
                await db.commit()
                raise
    finally:
        await eng.dispose()


def func_now():
    from datetime import datetime

    return datetime.now(UTC)


async def _followup_reminders() -> None:
    maker, eng = get_session_maker()
    try:
        async with maker() as db:
            events = (
                await db.scalars(
                    select(TimelineEvent).where(TimelineEvent.type == "prescription")
                )
            ).all()
            clinics = {
                c.id: c for c in (await db.scalars(select(Clinic))).all()
            }
            for event in events:
                followup = (event.payload or {}).get("followup_date")
                if not followup:
                    continue
                try:
                    followup_date = date.fromisoformat(str(followup))
                except ValueError:
                    continue
                patient = await db.get(Patient, event.patient_id)
                clinic = clinics.get(patient.clinic_id)
                settings_json = clinic.settings or {}
                days = int(settings_json.get("followup_reminder_days", 1))
                if followup_date != date.today() + timedelta(days=days):
                    continue
                dup = (
                    await db.scalars(
                        select(WhatsAppLog).where(
                            WhatsAppLog.patient_id == patient.id,
                            WhatsAppLog.template == "followup_reminder",
                            WhatsAppLog.body.like(f"%{followup_date.isoformat()}%"),
                        )
                    )
                ).first()
                if dup:
                    continue
                log_id = await _enqueue_whatsapp(
                    db,
                    patient.id,
                    "followup_reminder",
                    f"Reminder: {patient.name} has a follow-up at {clinic.name} on "
                    f"{followup_date.isoformat()}. - ClinicBrain",
                )
                if log_id:
                    send_whatsapp_task.delay(str(log_id))
    finally:
        await eng.dispose()


@celery_app.task(name="whatsapp.followup_reminders")
def followup_reminders_task() -> None:
    asyncio.run(_followup_reminders())


async def queue_message(db, patient_id: int, template: str, body: str) -> None:
    log_id = await _enqueue_whatsapp(db, patient_id, template, body)
    if log_id:
        send_whatsapp_task.delay(str(log_id))
