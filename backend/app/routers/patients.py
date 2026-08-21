from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import Patient, User
from app.schemas import PatientCreate, PatientOut

router = APIRouter(prefix="/api/patients", tags=["patients"])


async def _get_scoped_patient(patient_id: int, user: User, db: AsyncSession) -> Patient:
    patient = (
        await db.scalars(
            select(Patient).where(Patient.id == patient_id, Patient.clinic_id == user.clinic_id)
        )
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.post("", response_model=PatientOut)
async def create_patient(
    body: PatientCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    patient = Patient(clinic_id=user.clinic_id, **body.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return patient


@router.get("", response_model=list[PatientOut])
async def list_patients(
    q: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Patient).where(Patient.clinic_id == user.clinic_id)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Patient.name.ilike(pattern), Patient.phone.ilike(pattern)))
    rows = await db.scalars(stmt.order_by(Patient.name).limit(200))
    return list(rows)


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _get_scoped_patient(patient_id, user, db)
