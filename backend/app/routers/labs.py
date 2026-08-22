from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db import get_db
from app.models import LabResult, Patient, User
from app.routers.documents import _scoped_doc
from app.services.audit import audit
from app.validators import clean_number, compute_flag

router = APIRouter(prefix="/api", tags=["labs"])


class LabRowIn(BaseModel):
    test_name: str = Field(min_length=1, max_length=200)
    value: str | float
    unit: str | None = None
    ref_low: str | float | None = None
    ref_high: str | float | None = None
    taken_at: date | None = None


class ConfirmLabs(BaseModel):
    rows: list[LabRowIn] = Field(min_length=1)


def _num(v: str | float | None) -> float | None:
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    return clean_number(v)


@router.post("/documents/{doc_id}/confirm-labs")
async def confirm_labs(
    doc_id: int,
    body: ConfirmLabs,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _scoped_doc(doc_id, user, db)
    if doc.status != "needs_review":
        raise HTTPException(status_code=409, detail=f"Document is {doc.status}, not needs_review")

    parsed: list[LabResult] = []
    for i, row in enumerate(body.rows):
        try:
            value = clean_number(row.value)
            ref_low = _num(row.ref_low)
            ref_high = _num(row.ref_high)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=f"Row {i + 1}: {e}")
        parsed.append(
            LabResult(
                patient_id=doc.patient_id,
                document_id=doc.id,
                test_name=row.test_name.strip(),
                value=value,
                unit=row.unit,
                ref_low=ref_low,
                ref_high=ref_high,
                flag=compute_flag(value, ref_low, ref_high),
                taken_at=row.taken_at,
            )
        )

    for r in parsed:
        db.add(r)
    doc.status = "processed"
    lines = [
        f"{r.test_name}: {r.value} {r.unit or ''} ({r.flag})".replace("  ", " ") for r in parsed
    ]
    from app.models import TimelineEvent

    db.add(
        TimelineEvent(
            patient_id=doc.patient_id,
            type="lab",
            event_date=parsed[0].taken_at,
            payload={
                "summary": f"{len(parsed)} lab results",
                "content_text": "\n".join(lines),
                "document_id": doc.id,
            },
            created_by=user.id,
        )
    )
    await audit(db, user_id=user.id, action="confirm_labs", entity="document", entity_id=doc.id)
    await db.commit()
    return {"ok": True, "inserted": len(parsed)}


@router.post("/documents/{doc_id}/extract-labs")
async def reextract_labs(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    doc = await _scoped_doc(doc_id, user, db)
    if doc.status != "needs_review":
        raise HTTPException(status_code=409, detail=f"Document is {doc.status}, not needs_review")

    from app.workers import tasks as worker_tasks

    worker_tasks.extract_labs_task.delay(str(doc.id))
    return {"status": "queued"}


async def _patient_labs(patient_id: int, user: User, db: AsyncSession) -> list[LabResult]:
    patient = (
        await db.scalars(
            select(Patient).where(Patient.id == patient_id, Patient.clinic_id == user.clinic_id)
        )
    ).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    rows = await db.scalars(
        select(LabResult)
        .where(LabResult.patient_id == patient.id)
        .order_by(LabResult.created_at.asc())
    )
    return list(rows)


@router.get("/patients/{patient_id}/labs")
async def patient_labs(
    patient_id: int,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await _patient_labs(patient_id, user, db)
    by_test: dict[str, list[LabResult]] = {}
    for r in rows:
        by_test.setdefault(r.test_name, []).append(r)

    out = []
    for test_name, items in sorted(by_test.items()):
        latest = items[-1]
        out.append(
            {
                "test_name": test_name,
                "value": float(latest.value),
                "unit": latest.unit,
                "flag": latest.flag,
                "taken_at": latest.taken_at.isoformat() if latest.taken_at else None,
                "count": len(items),
            }
        )
    return out


@router.get("/patients/{patient_id}/labs/trend")
async def lab_trend(
    patient_id: int,
    test_name: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = await _patient_labs(patient_id, user, db)
    series = [r for r in rows if r.test_name == test_name]
    return [
        {
            "value": float(r.value),
            "flag": r.flag,
            "unit": r.unit,
            "ref_low": float(r.ref_low) if r.ref_low is not None else None,
            "ref_high": float(r.ref_high) if r.ref_high is not None else None,
            "taken_at": r.taken_at.isoformat() if r.taken_at else r.created_at.date().isoformat(),
        }
        for r in series
    ]
