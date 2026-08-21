# ClinicBrain — Design Document

**Date:** 2026-08-21
**Status:** Approved (pending implementation plan)
**Author:** Akshar Rai

## 1. Summary

ClinicBrain is a web platform for small Indian clinics (single-doctor and mixed practices). Its pitch: **"The AI memory of the clinic."**

It combines four modules on top of one shared Patient Timeline:

1. **Records Digitizer** — scan/photograph paper prescriptions, reports, letters → OCR/AI extraction → searchable patient history.
2. **AI Lab Report Reader** — photograph a lab report → AI extracts test values → abnormal flags → automatic trend charts.
3. **Queue + WhatsApp Follow-ups** — token management, live queue updates, appointment confirmations, and automated follow-up reminders via WhatsApp.
4. **AI Prescription Safety Checker** — real-time allergy, drug-interaction, and dosage warnings while the doctor prescribes.

## 2. Goals & Non-Goals

### Goals
- Digitize all clinic paper records into one searchable timeline per patient.
- Save doctor time per consultation and reduce missed follow-ups.
- Every AI output is a **draft requiring one-tap human confirmation** — the core trust feature.
- Sellable to a single-doctor clinic as a monthly SaaS.

### Non-Goals (v1)
- Billing/GST/inventory management.
- Telemedicine video calls.
- ABDM/ABHA integration (deferred to v2).
- Multi-language UI beyond English + Hindi labels.
- On-premise deployment (cloud-only in v1).

## 3. Users & Context

- **Doctor:** consults 20–50 patients/day; wants fast records recall and safe prescribing.
- **Receptionist:** manages tokens, scans papers, confirms AI drafts.
- **Patient:** receives WhatsApp messages only (no app install).
- Market: Indian small clinics; mixed Hindi/English usage; unreliable connectivity tolerated via graceful degradation.

## 4. Architecture

```
                    ┌─────────────────────────┐
                    │     PATIENT TIMELINE     │
                    │  (single source of truth) │
                    └────────────┬────────────┘
        writes ↑                 │ ↑ reads              ↑ writes
┌───────────────┐   ┌────────────┴──────────┐   ┌────────────────┐
│ Lab Report    │   │  Records Digitizer    │   │ Queue +        │
│ Reader (AI)   │   │  (scan old papers,    │   │ WhatsApp       │
│               │   │   OCR → timeline)     │   │ Follow-ups     │
└───────────────┘   └───────────────────────┘   └────────────────┘
                   ┌───────────────────────┐
                   │ Rx Safety Checker(AI) │ ← reads timeline while
                   │ (interactions/allergy)│    doctor prescribes
                   └───────────────────────┘
```

Every module is a reader or writer of `timeline_events`. This is what makes ClinicBrain one product rather than four tools.

### Tech Stack

| Layer | Choice | Rationale |
|---|---|---|
| Frontend | React + Tailwind CSS | Fast development, familiar stack |
| Backend | Python FastAPI | Team skill fit; best AI ecosystem |
| Database | PostgreSQL + pgvector | Relational core + vector search for similar-case lookup |
| Vision/extraction LLM | GPT-4o-mini vision (primary), Gemini Flash (fallback) | Handles messy phone photos of reports; fallback avoids single-provider outage |
| Safety checks | Rules engine + LLM hybrid | Deterministic rules for hard facts; LLM for context only |
| WhatsApp | Meta WhatsApp Cloud API | Official API, free tier, India-ready |
| File storage | Cloudflare R2 (S3-compatible) | Cheap scan/report storage, no egress fees |
| Background jobs | Celery + Redis | OCR/extraction jobs, reminder crons, retries |
| Deployment | Docker Compose on a VPS | Low startup cost |

## 5. Data Model

```
clinics(id, name, address, phone, settings JSONB)
users(id, clinic_id FK, name, role: doctor|receptionist, phone, password_hash)
patients(id, clinic_id FK, name, phone, dob, gender,
         allergies TEXT[], chronic_conditions TEXT[])
timeline_events(id, patient_id FK, type: visit|prescription|lab|document|note,
                event_date, payload JSONB, created_by FK users)   -- CORE TABLE
documents(id, patient_id FK, s3_key, ocr_text, status: pending|processed|failed)
lab_results(id, patient_id FK, document_id FK NULL, test_name, value NUMERIC,
            unit, ref_low, ref_high, flag: normal|high|low|review, taken_at)
prescriptions(id, patient_id FK, doctor_id FK, meds JSONB,
              safety_warnings JSONB, followup_date DATE)
queue_tokens(id, clinic_id FK, patient_id FK, date, number INT,
             status: waiting|in_consult|done, checked_in_at)
whatsapp_log(id, patient_id FK, template, status: sent|failed|retrying, retries INT)
drug_reference(id, name, interactions TEXT[], max_dose, contraindications TEXT[])
audit_log(id, user_id FK, entity, entity_id, action, at)
```

All queries are scoped by `clinic_id` (row-level isolation).

## 6. Key Data Flows

1. **Scan digitizer:** photo upload → background job → vision LLM extracts text + document type → saved as **draft** → staff reviews/confirms → `timeline_events` row created.
2. **Lab reader:** photo → LLM extracts `{test_name, value, unit, ref_low, ref_high}` rows → values regex-validated, test names matched against master list → draft table shown → confirm → `lab_results` stored → trend chart auto-generated.
3. **Queue/WhatsApp:** token issued → WhatsApp confirmation sent → doctor taps "Next" → patient receives "Your turn" message → if prescription has `followup_date`, cron sends a reminder 1 day before (default, configurable per clinic).
4. **Rx safety:** as doctor types each drug → instant parallel checks: patient allergy list (**hard block**), drug-drug interactions from `drug_reference` (**warning**), dose vs `max_dose` (**warning**) → shown inline before save.

## 7. Error Handling & Trust Rules

- **AI never auto-saves.** All extraction output is a draft requiring explicit human confirmation.
- Extraction job failure → document marked `failed`; manual entry offered.
- WhatsApp send failure → retry ×3 with exponential backoff → surfaced on staff dashboard.
- Unknown test names or unparseable values → flagged `review` (yellow), never silently dropped.
- LLM hallucination guard: numeric fields must pass regex validation before entering drafts.
- All data clinic-isolated; every read/write of clinical records appended to `audit_log`.

## 8. Security & Compliance

- Per-clinic data isolation enforced at query layer.
- Passwords hashed (argon2); JWT auth with short expiry.
- Patient consent captured for WhatsApp messaging (DPDP Act awareness).
- Audit log immutable (append-only).
- Secrets via environment variables only; never committed.

## 9. Testing Strategy

- **Golden set:** ~50 real report photos collected from partner clinic; automated field-level extraction accuracy score (target >90%).
- Unit tests: safety rules engine, value parsers, date logic.
- Integration tests: API flows per module.
- E2E: book token → consult → prescribe → follow-up reminder.
- Weekly human evaluation of LLM drafts during pilot.

## 10. Build Phases (all within v1)

1. **Phase 1:** Data core + Records Digitizer (upload → extract → searchable timeline).
2. **Phase 2:** Lab Report Reader (extraction → values → trends).
3. **Phase 3:** Queue + WhatsApp confirmations/reminders.
4. **Phase 4:** Rx Safety Checker (rich timeline data from phases 1–2 makes it useful).

Each phase ends deployable and demoable to partner clinics.

## 11. Success Criteria

- Partner clinic processes ≥80% of daily paper through the digitizer within 4 weeks.
- Lab extraction field accuracy >90% on golden set.
- Zero silent data loss (every failed item visible in review queue).
- Doctor can retrieve any patient's full history in <10 seconds.
