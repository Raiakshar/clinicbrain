import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth import hash_password
from app.config import settings
from app.models import Base, Clinic, Patient, TimelineEvent, User


async def main() -> None:
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as db:
        existing = await db.scalar(select(User).where(User.phone == "9811111111"))
        if existing:
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

        for name, phone in [("Ramesh Gupta", "9765432101"), ("Sunita Devi", "9765432102")]:
            patient = Patient(clinic_id=clinic.id, name=name, phone=phone, gender="male" if name.startswith("R") else "female")
            db.add(patient)
            await db.flush()
            db.add(
                TimelineEvent(
                    patient_id=patient.id,
                    type="note",
                    payload={"text": "First visit: general checkup, BP normal."},
                    created_by=doctor.id,
                )
            )

        await db.commit()
        print("Seeded: login 9811111111 / demo1234")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
