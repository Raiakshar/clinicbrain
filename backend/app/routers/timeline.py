from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import TimelineEvent, User
from app.routers.patients import _get_scoped_patient
from app.schemas import EventCreate, EventOut

router = APIRouter(prefix="/api/patients", tags=["timeline"])


@router.post("/{patient_id}/events", response_model=EventOut)
async def add_event(
    patient_id: int,
    body: EventCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    patient = await _get_scoped_patient(patient_id, user, db)
    event = TimelineEvent(
        patient_id=patient.id,
        type=body.type,
        event_date=body.event_date,
        payload=body.payload,
        created_by=user.id,
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("/{patient_id}/events", response_model=list[EventOut])
async def list_events(
    patient_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    patient = await _get_scoped_patient(patient_id, user, db)
    rows = await db.scalars(
        select(TimelineEvent)
        .where(TimelineEvent.patient_id == patient.id)
        .order_by(TimelineEvent.event_date.desc().nulls_last(), TimelineEvent.created_at.desc())
    )
    return list(rows)
