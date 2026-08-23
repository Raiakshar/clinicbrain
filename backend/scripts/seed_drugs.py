import asyncio

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db import SessionLocal
from app.models import DrugReference
from app.services.rx_safety import INTERACTIONS

DRUGS = [
    ("Amoxicillin", "amoxicillin", "penicillin", 3000),
    ("Azithromycin", "azithromycin", "macrolide", 500),
    ("Clarithromycin", "clarithromycin", "macrolide", 1000),
    ("Cefixime", "cefixime", "cephalosporin", 800),
    ("Cotrimoxazole", "trimethoprim-sulfamethoxazole", "sulfonamide", 1920),
    ("Doxycycline", "doxycycline", "tetracycline", 300),
    ("Metronidazole", "metronidazole", "nitroimidazole", 1500),
    ("Ciprofloxacin", "ciprofloxacin", "fluoroquinolone", 1500),
    ("Ofloxacin", "ofloxacin", "fluoroquinolone", 800),
    ("Norfloxacin", "norfloxacin", "fluoroquinolone", 800),
    ("Metformin", "metformin", "biguanide", 3000),
    ("Glimepiride", "glimepiride", "sulfonylurea", 8),
    ("Amlodipine", "amlodipine", "calcium channel blocker", 10),
    ("Telmisartan", "telmisartan", "arb", 80),
    ("Losartan", "losartan", "arb", 100),
    ("Enalapril", "enalapril", "ace inhibitor", 40),
    ("Hydrochlorothiazide", "hydrochlorothiazide", "thiazide diuretic", 50),
    ("Spironolactone", "spironolactone", "potassium-sparing diuretic", 100),
    ("Atorvastatin", "atorvastatin", "statin", 80),
    ("Rosuvastatin", "rosuvastatin", "statin", 40),
    ("Aspirin", "aspirin", "antiplatelet", 4000),
    ("Clopidogrel", "clopidogrel", "antiplatelet", 600),
    ("Warfarin", "warfarin", "anticoagulant", 10),
    ("Ibuprofen", "ibuprofen", "nsaid", 2400),
    ("Diclofenac", "diclofenac", "nsaid", 150),
    ("Paracetamol", "paracetamol", "analgesic antipyretic", 4000),
    ("Tramadol", "tramadol", "opioid analgesic", 400),
    ("Pantoprazole", "pantoprazole", "proton pump inhibitor", 80),
    ("Omeprazole", "omeprazole", "proton pump inhibitor", 40),
    ("Domperidone", "domperidone", "prokinetic", 30),
    ("Ondansetron", "ondansetron", "antiemetic", 24),
    ("Cetirizine", "cetirizine", "antihistamine", 10),
    ("Levocetirizine", "levocetirizine", "antihistamine", 5),
    ("Montelukast", "montelukast", "leukotriene antagonist", 10),
    ("Salbutamol", "salbutamol", "beta2 agonist", 12),
    ("Prednisolone", "prednisolone", "corticosteroid", 60),
    ("Dexamethasone", "dexamethasone", "corticosteroid", 16),
    ("Levothyroxine", "levothyroxine", "thyroid hormone", 300),
    ("Carbamazepine", "carbamazepine", "anticonvulsant", 1600),
    ("Sertraline", "sertraline", "ssri antidepressant", 200),
    ("Escitalopram", "escitalopram", "ssri antidepressant", 20),
    ("Amitriptyline", "amitriptyline", "tricyclic antidepressant", 150),
    ("Alprazolam", "alprazolam", "benzodiazepine", 4),
]


async def seed() -> int:
    async with SessionLocal() as db:
        for name, generic, cls, max_mg in DRUGS:
            stmt = (
                pg_insert(DrugReference)
                .values(
                    name=name,
                    generic_name=generic,
                    drug_class=cls,
                    max_daily_dose_mg=max_mg,
                )
                .on_conflict_do_nothing(index_elements=["name"])
            )
            await db.execute(stmt)
        await db.commit()
        count = len((await db.scalars(select(DrugReference))).all())
        print(f"drug_reference rows: {count}")
        print(f"interaction pairs loaded from rules engine: {len(INTERACTIONS)}")
        return count


if __name__ == "__main__":
    asyncio.run(seed())
