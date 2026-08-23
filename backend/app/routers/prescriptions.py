import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import (
    DrugReference,
    Patient,
    Prescription,
    PrescriptionItem,
    TimelineEvent,
    User,
)
from app.schemas import AllergiesUpdate, RxCheckRequest, RxSaveRequest
from app.services.audit import audit
from app.services.rx_safety import check_prescription

router = APIRouter(tags=["rx"])


async def _scoped_patient(patient_id: int, user: User, db: AsyncSession) -> Patient:
    patient = (
        await db.scalars(
            select(Patient).where(Patient.id == patient_id, Patient.clinic_id == user.clinic_id)
        )
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@router.get("/api/drugs")
async def list_drugs(
    q: str | None = None,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(DrugReference)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            DrugReference.name.ilike(pattern) | DrugReference.generic_name.ilike(pattern)
        )
    rows = (await db.scalars(stmt.order_by(DrugReference.name).limit(20))).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "generic_name": d.generic_name,
            "drug_class": d.drug_class,
            "max_daily_dose_mg": float(d.max_daily_dose_mg) if d.max_daily_dose_mg else None,
        }
        for d in rows
    ]


@router.put("/api/patients/{patient_id}/allergies")
async def update_allergies(
    patient_id: int,
    body: AllergiesUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    patient = await _scoped_patient(patient_id, user, db)
    patient.allergies = [a.strip() for a in body.allergies if a.strip()]
    await audit(db, user_id=user.id, action="update", entity="patient_allergies", entity_id=patient.id)
    await db.commit()
    return {"id": patient.id, "allergies": patient.allergies}


def _report_out(report):
    return {"blocks": report.blocks, "warnings": report.warnings}


@router.post("/api/patients/{patient_id}/check-rx")
async def check_rx(
    patient_id: int,
    body: RxCheckRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    patient = await _scoped_patient(patient_id, user, db)
    report, _ = await check_prescription(db, patient, [i.model_dump() for i in body.items])
    return _report_out(report)


@router.post("/api/patients/{patient_id}/prescriptions")
async def save_prescription(
    patient_id: int,
    body: RxSaveRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    patient = await _scoped_patient(patient_id, user, db)
    items = [i.model_dump() for i in body.items]
    report, _ = await check_prescription(db, patient, items)

    if report.blocks:
        raise HTTPException(
            status_code=400,
            detail={"message": "Blocked by allergy hard-stop", **_report_out(report)},
        )
    if report.warnings and not body.acknowledged_warnings:
        raise HTTPException(
            status_code=409,
            detail={"message": "Warnings need acknowledgment before saving", **_report_out(report)},
        )

    rx = Prescription(patient_id=patient.id, prescriber_id=user.id, notes=body.notes)
    db.add(rx)
    await db.flush()
    for item in items:
        db.add(PrescriptionItem(prescription_id=rx.id, **item))

    summary = ", ".join(f"{i['drug_name']} {i['dose_mg']:.0f}mg x{i['frequency_per_day']}/day" for i in items)
    payload = {"summary": summary}
    if body.followup_date:
        payload["followup_date"] = body.followup_date.isoformat()
    if report.warnings and body.acknowledged_warnings:
        payload["warnings_acknowledged"] = report.warnings
    db.add(TimelineEvent(patient_id=patient.id, type="prescription", event_date=dt.date.today(), payload=payload))
    await audit(db, user_id=user.id, action="create", entity="prescription", entity_id=rx.id)
    await db.commit()
    return {"id": rx.id, "warnings_acknowledged": bool(report.warnings)}


@router.get("/api/patients/{patient_id}/prescriptions")
async def list_prescriptions(
    patient_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    patient = await _scoped_patient(patient_id, user, db)
    rxs = (
        await db.scalars(
            select(Prescription)
            .where(Prescription.patient_id == patient.id)
            .order_by(Prescription.created_at.desc())
        )
    ).all()
    out = []
    for rx in rxs:
        items = (
            await db.scalars(
                select(PrescriptionItem).where(PrescriptionItem.prescription_id == rx.id)
            )
        ).all()
        out.append(
            {
                "id": rx.id,
                "created_at": rx.created_at.isoformat() if rx.created_at else None,
                "notes": rx.notes,
                "items": [
                    {
                        "drug_name": i.drug_name,
                        "dose_mg": float(i.dose_mg),
                        "frequency_per_day": i.frequency_per_day,
                        "duration_days": i.duration_days,
                        "instructions": i.instructions,
                    }
                    for i in items
                ],
            }
        )
    return out
