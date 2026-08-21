import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Document, Patient, User
from app.routers.patients import _get_scoped_patient
from app.schemas import ConfirmPayload
from app.services.audit import audit
from app.services.storage import Storage, get_storage
from app.validators import validate_extraction

router = APIRouter(prefix="/api", tags=["documents"])

EVENT_TYPE_MAP = {"prescription": "prescription", "lab": "lab"}


async def _scoped_doc(doc_id: int, user: User, db: AsyncSession) -> Document:
    doc = (
        await db.scalars(
            select(Document).join(Patient, Document.patient_id == Patient.id).where(
                Document.id == doc_id, Patient.clinic_id == user.clinic_id
            )
        )
    ).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/patients/{patient_id}/documents")
async def upload_document(
    patient_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    patient = await _get_scoped_patient(patient_id, user, db)
    data = await file.read()
    ext = Path(file.filename or "scan.jpg").suffix.lstrip(".") or "jpg"
    key = f"patients/{patient.id}/{uuid.uuid4().hex}.{ext}"
    storage.put(key, data, file.content_type or "image/jpeg")
    doc = Document(
        patient_id=patient.id,
        s3_key=key,
        mime=file.content_type or "image/jpeg",
        uploaded_by=user.id,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    from app.workers import tasks as worker_tasks

    worker_tasks.extract_document_task.delay(str(doc.id))
    return {"id": doc.id, "status": doc.status}


@router.get("/documents")
async def list_documents(
    status: str | None = None,
    patient_id: int | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Document)
        .join(Patient, Document.patient_id == Patient.id)
        .where(Patient.clinic_id == user.clinic_id)
    )
    if status:
        stmt = stmt.where(Document.status == status)
    if patient_id:
        stmt = stmt.where(Document.patient_id == patient_id)
    rows = await db.scalars(stmt.order_by(Document.created_at.desc()).limit(200))
    return [
        {
            "id": d.id,
            "patient_id": d.patient_id,
            "status": d.status,
            "mime": d.mime,
            "error": d.error,
            "ocr_text": d.ocr_text,
            "extracted": d.extracted,
            "created_at": d.created_at.isoformat() if d.created_at else None,
        }
        for d in rows
    ]


@router.get("/documents/{doc_id}/file")
async def get_document_file(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    doc = await _scoped_doc(doc_id, user, db)
    data = storage.get(doc.s3_key)
    return Response(content=data, media_type=doc.mime)


@router.post("/documents/{doc_id}/confirm")
async def confirm_document(
    doc_id: int,
    body: ConfirmPayload,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        validate_extraction(body.summary, body.content_text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    doc = await _scoped_doc(doc_id, user, db)
    if doc.status != "needs_review":
        raise HTTPException(status_code=409, detail=f"Document is {doc.status}, not needs_review")
    from app.models import TimelineEvent

    event_type = EVENT_TYPE_MAP.get(body.document_type, "document")
    event_date = body.event_date
    extracted = doc.extracted or {}
    if event_date is None and extracted.get("event_date"):
        try:
            import datetime as dt

            event_date = dt.date.fromisoformat(str(extracted["event_date"]))
        except ValueError:
            event_date = None
    event = TimelineEvent(
        patient_id=doc.patient_id,
        type=event_type,
        event_date=event_date,
        payload={
            "summary": body.summary,
            "content_text": body.content_text,
            "document_id": doc.id,
        },
        created_by=user.id,
    )
    db.add(event)
    doc.status = "processed"
    await audit(db, user_id=user.id, action="confirm", entity="document", entity_id=doc.id)
    await db.commit()
    return {"ok": True}


@router.post("/documents/{doc_id}/reject", status_code=204)
async def reject_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    doc = await _scoped_doc(doc_id, user, db)
    try:
        storage.delete(doc.s3_key)
    except Exception as e:
        print(f"storage delete failed for {doc.s3_key}: {e}")
    await db.delete(doc)
    await audit(db, user_id=user.id, action="reject", entity="document", entity_id=doc.id)
    await db.commit()


@router.post("/documents/{doc_id}/retry")
async def retry_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _scoped_doc(doc_id, user, db)
    if doc.status != "failed":
        raise HTTPException(status_code=409, detail=f"Document is {doc.status}, not failed")
    doc.status = "pending"
    doc.error = None
    await db.commit()

    from app.workers import tasks as worker_tasks

    worker_tasks.extract_document_task.delay(str(doc.id))
    return {"status": "pending"}
