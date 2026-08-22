import asyncio
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth import hash_password
from app.config import settings
from app.models import Base, Clinic, LabResult, LabTest, Patient, TimelineEvent, User

LAB_TESTS = [
    ("Hemoglobin", "g/dL"),
    ("WBC Count", "cells/µL"),
    ("Platelet Count", "cells/µL"),
    ("Fasting Glucose", "mg/dL"),
    ("Postprandial Glucose", "mg/dL"),
    ("HbA1c", "%"),
    ("Total Cholesterol", "mg/dL"),
    ("LDL Cholesterol", "mg/dL"),
    ("HDL Cholesterol", "mg/dL"),
    ("Triglycerides", "mg/dL"),
    ("SGPT (ALT)", "U/L"),
    ("SGOT (AST)", "U/L"),
    ("Serum Creatinine", "mg/dL"),
    ("Blood Urea", "mg/dL"),
    ("Uric Acid", "mg/dL"),
    ("TSH", "µIU/mL"),
    ("Vitamin D (25-OH)", "ng/mL"),
    ("Vitamin B12", "pg/mL"),
    ("Serum Sodium", "mmol/L"),
    ("Serum Potassium", "mmol/L"),
]


async def main() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        for name, unit in LAB_TESTS:
            exists = await db.scalar(select(LabTest).where(LabTest.name == name))
            if not exists:
                db.add(LabTest(name=name, unit=unit))

        existing = await db.scalar(select(User).where(User.phone == "9811111111"))
        if existing:
            await db.commit()
            print("Demo data already present")
            await engine.dispose()
            return

        clinic = Clinic(name="Sunrise Clinic", phone="0112345678")
        db.add(clinic)
        await db.flush()

        doctor = User(
            clinic_id=clinic.id,
            name="Dr Sharma",
            role="doctor",
            phone="9811111111",
            password_hash=hash_password("demo1234"),
        )
        db.add(doctor)
        await db.flush()

        ramesh = Patient(clinic_id=clinic.id, name="Ramesh Gupta", phone="9765432101", gender="male")
        sunita = Patient(clinic_id=clinic.id, name="Sunita Devi", phone="9765432102", gender="female")
        db.add_all([ramesh, sunita])
        await db.flush()

        db.add(
            TimelineEvent(
                patient_id=sunita.id,
                type="note",
                payload={"text": "First visit: general checkup, BP normal."},
                created_by=doctor.id,
            )
        )

        d = date.fromisoformat
        history = [
            ("HbA1c", 8.9, d("2026-02-10"), "high"),
            ("HbA1c", 8.4, d("2026-04-14"), "high"),
            ("HbA1c", 7.8, d("2026-06-20"), "high"),
            ("Fasting Glucose", 172, d("2026-02-10"), "high"),
            ("Fasting Glucose", 148, d("2026-06-20"), "high"),
            ("Hemoglobin", 13.4, d("2026-02-10"), "normal"),
            ("Hemoglobin", 10.2, d("2026-06-20"), "low"),
        ]
        for test, value, taken, flag in history:
            unit = next(u for n, u in LAB_TESTS if n == test)
            ref_low, ref_high = (4.0, 5.6) if test == "HbA1c" else ((70, 100) if "Glucose" in test else (13.0, 17.0))
            db.add(
                LabResult(
                    patient_id=ramesh.id,
                    test_name=test,
                    value=value,
                    unit=unit,
                    ref_low=ref_low,
                    ref_high=ref_high,
                    flag=flag,
                    taken_at=taken,
                )
            )
        db.add(
            TimelineEvent(
                patient_id=ramesh.id,
                type="lab",
                event_date=date(2026, 6, 20),
                payload={
                    "summary": "3 lab results",
                    "content_text": "HbA1c: 7.8 % (high)\nFasting Glucose: 148 mg/dL (high)\nHemoglobin: 10.2 g/dL (low)",
                },
                created_by=doctor.id,
            )
        )

        await db.commit()
        print("Seeded: login 9811111111 / demo1234")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
