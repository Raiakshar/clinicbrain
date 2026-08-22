import datetime as dt

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Clinic, Patient, QueueToken, User, WhatsAppLog
from app.services.audit import audit
from app.workers.tasks import queue_message

router = APIRouter(prefix="/api/queue", tags=["queue"])


class CheckInRequest(BaseModel):
    patient_id: int


def _today() -> dt.date:
    return dt.date.today()


async def _scoped_token(token_id: int, user: User, db: AsyncSession) -> QueueToken:
    token = (
        await db.scalars(
            select(QueueToken).where(
                QueueToken.id == token_id, QueueToken.clinic_id == user.clinic_id
            )
        )
    ).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    return token


@router.post("/check-in")
async def check_in(
    body: CheckInRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    patient = (
        await db.scalars(
            select(Patient).where(
                Patient.id == body.patient_id, Patient.clinic_id == user.clinic_id
            )
        )
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    existing = (
        await db.scalars(
            select(QueueToken).where(
                QueueToken.patient_id == patient.id,
                QueueToken.date == _today(),
                QueueToken.status != "done",
            )
        )
    ).first()
    if existing:
        return {"id": existing.id, "number": existing.number, "status": existing.status}

    max_number = await db.scalar(
        select(func.max(QueueToken.number)).where(
            QueueToken.clinic_id == user.clinic_id, QueueToken.date == _today()
        )
    )
    token = QueueToken(
        clinic_id=user.clinic_id,
        patient_id=patient.id,
        date=_today(),
        number=(max_number or 0) + 1,
    )
    db.add(token)
    await audit(db, user_id=user.id, action="check_in", entity="queue_token", entity_id=None)
    await db.commit()
    await db.refresh(token)

    clinic = await db.get(Clinic, user.clinic_id)
    await queue_message(
        db,
        patient.id,
        "token_confirmation",
        f"Namaste {patient.name}, you are #{token.number} in the queue at {clinic.name} "
        f"for {_today().isoformat()}. - ClinicBrain",
    )
    return {"id": token.id, "number": token.number, "status": token.status}


@router.get("/today")
async def today_queue(
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(QueueToken, Patient)
        .join(Patient, QueueToken.patient_id == Patient.id)
        .where(QueueToken.clinic_id == user.clinic_id, QueueToken.date == _today())
    )
    if status:
        stmt = stmt.where(QueueToken.status == status)
    rows = (await db.execute(stmt.order_by(QueueToken.number))).all()
    return [
        {
            "id": t.id,
            "number": t.number,
            "status": t.status,
            "patient_id": p.id,
            "patient_name": p.name,
            "patient_phone": p.phone,
            "checked_in_at": t.checked_in_at.isoformat() if t.checked_in_at else None,
        }
        for t, p in rows
    ]


@router.post("/{token_id}/call")
async def call_token(
    token_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token = await _scoped_token(token_id, user, db)
    if token.status != "waiting":
        raise HTTPException(status_code=409, detail=f"Token is {token.status}, not waiting")
    in_consult = (
        await db.scalars(
            select(QueueToken).where(
                QueueToken.clinic_id == user.clinic_id,
                QueueToken.date == _today(),
                QueueToken.status == "in_consult",
            )
        )
    ).first()
    if in_consult:
        raise HTTPException(status_code=409, detail="Another patient is in consult")

    token.status = "in_consult"
    await db.commit()

    patient = await db.get(Patient, token.patient_id)
    await queue_message(
        db,
        patient.id,
        "your_turn",
        f"Namaste {patient.name}, it is your turn now. Please come to the doctor's room. - ClinicBrain",
    )
    return {"id": token.id, "status": token.status}


@router.post("/{token_id}/complete")
async def complete_token(
    token_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    token = await _scoped_token(token_id, user, db)
    if token.status != "in_consult":
        raise HTTPException(status_code=409, detail=f"Token is {token.status}, not in_consult")
    token.status = "done"
    await audit(db, user_id=user.id, action="complete", entity="queue_token", entity_id=token.id)
    await db.commit()
    return {"id": token.id, "status": token.status}


@router.get("/whatsapp-log")
async def whatsapp_log_view(
    status: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(WhatsAppLog, Patient.name)
        .join(Patient, WhatsAppLog.patient_id == Patient.id)
        .where(Patient.clinic_id == user.clinic_id)
    )
    if status:
        stmt = stmt.where(WhatsAppLog.status == status)
    rows = (await db.execute(stmt.order_by(WhatsAppLog.created_at.desc()).limit(100))).all()
    return [
        {
            "id": w.id,
            "patient_name": name,
            "template": w.template,
            "body": w.body,
            "status": w.status,
            "retries": w.retries,
            "error": w.error,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w, name in rows
    ]
