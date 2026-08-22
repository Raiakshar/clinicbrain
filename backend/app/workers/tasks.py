import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.models import Document
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


from app.models import Document


@celery_app.task(name="documents.extract")
def extract_document_task(document_id: str) -> None:
    asyncio.run(_run(int(document_id), "full"))


@celery_app.task(name="documents.extract_labs")
def extract_labs_task(document_id: str) -> None:
    asyncio.run(_run(int(document_id), "labs"))
