from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DrugReference, Patient, Prescription, PrescriptionItem


@dataclass
class SafetyReport:
    blocks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


INTERACTIONS: dict[frozenset[str], str] = {
    frozenset({"warfarin", "aspirin"}): "Major bleeding risk",
    frozenset({"warfarin", "ibuprofen"}): "Major bleeding risk",
    frozenset({"warfarin", "diclofenac"}): "Major bleeding risk",
    frozenset({"enalapril", "ibuprofen"}): "NSAID reduces BP control, renal risk",
    frozenset({"telmisartan", "ibuprofen"}): "NSAID reduces BP control, renal risk",
    frozenset({"losartan", "ibuprofen"}): "NSAID reduces BP control, renal risk",
    frozenset({"enalapril", "spironolactone"}): "Hyperkalemia risk",
    frozenset({"clopidogrel", "omeprazole"}): "Omeprazole reduces clopidogrel effect (CYP2C19)",
    frozenset({"atorvastatin", "clarithromycin"}): "Myopathy risk (CYP3A4 inhibition)",
    frozenset({"rosuvastatin", "clarithromycin"}): "Myopathy risk",
    frozenset({"metformin", "glimepiride"}): "Additive hypoglycemia risk",
    frozenset({"sertraline", "aspirin"}): "Serotonin syndrome + bleeding risk",
    frozenset({"sertraline", "warfarin"}): "Bleeding risk",
    frozenset({"escitalopram", "amitriptyline"}): "QT prolongation + serotonin risk",
    frozenset({"tramadol", "alprazolam"}): "CNS/respiratory depression risk",
    frozenset({"tramadol", "clonazepam"}): "CNS/respiratory depression risk",
    frozenset({"ciprofloxacin", "ondansetron"}): "QT prolongation risk",
}

ALLERGY_CLASS_MAP: dict[str, str] = {
    "penicillin": "penicillin",
    "sulfa": "sulfonamide",
    "sulfonamide": "sulfonamide",
    "nsaid": "nsaid",
    "aspirin": "antiplatelet",
}


def _norm(s: str) -> str:
    return s.strip().lower()


def _allergy_matches(allergies: list[str], drug) -> bool:
    for allergy in allergies or []:
        a = _norm(allergy)
        mapped_class = ALLERGY_CLASS_MAP.get(a)
        if mapped_class and drug.drug_class == mapped_class:
            return True
        if drug.name and a in _norm(drug.name):
            return True
        if drug.generic_name and a in _norm(drug.generic_name):
            return True
        if drug.drug_class and a in _norm(drug.drug_class):
            return True
        if len(a) >= 4 and a in _norm(drug.name or ""):
            return True
    return False


async def check_prescription(
    db: AsyncSession,
    patient: Patient,
    items: list[dict],
    include_history: bool = True,
) -> tuple[SafetyReport, dict[str, DrugReference]]:
    report = SafetyReport()
    names = [_norm(i["drug_name"]) for i in items]
    ref_rows = (await db.scalars(select(DrugReference))).all()
    refs = {_norm(d.name): d for d in ref_rows}

    for item in items:
        drug = refs.get(_norm(item["drug_name"]))
        label = f"{item['drug_name']} {item['dose_mg']}mg x{item['frequency_per_day']}/day"
        if not drug:
            report.warnings.append(f"{item['drug_name']}: not in reference list — verify dose manually")
            continue
        if _allergy_matches(patient.allergies or [], drug):
            report.blocks.append(f"ALLERGY: {label} conflicts with recorded allergy ({', '.join(patient.allergies or [])})")
            continue
        max_dose = float(drug.max_daily_dose_mg) if drug.max_daily_dose_mg else None
        daily_total = float(item["dose_mg"]) * int(item.get("frequency_per_day") or 1)
        if max_dose and daily_total > max_dose:
            report.warnings.append(
                f"MAX DOSE: {label} exceeds max {max_dose:.0f}mg/day for {drug.name}"
            )

    present = set(names)

    def _disp(n: str) -> str:
        return refs[n].name if n in refs else n.title()

    for pair, reason in INTERACTIONS.items():
        hits = pair & present
        if len(hits) == 2:
            report.warnings.append(
                f"INTERACTION: {' + '.join(sorted(_disp(n) for n in hits))} — {reason}"
            )

    if include_history:
        prior_rx_ids = (
            await db.scalars(
                select(Prescription.id).where(Prescription.patient_id == patient.id)
            )
        ).all()
        recent_drugs: set[str] = set()
        if prior_rx_ids:
            rows = (
                await db.scalars(
                    select(PrescriptionItem).where(
                        PrescriptionItem.prescription_id.in_(prior_rx_ids)
                    )
                )
            ).all()
            recent_drugs = {_norm(r.drug_name) for r in rows}
        for pair, reason in INTERACTIONS.items():
            inter = pair & present
            rest = pair - inter
            if len(inter) == 1 and rest and rest & recent_drugs:
                report.warnings.append(
                    f"INTERACTION with existing medication: "
                    f"{' + '.join(sorted(_disp(n) for n in pair))} — {reason}"
                )
    return report, refs
