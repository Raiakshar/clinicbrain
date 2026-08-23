# ClinicBrain

**The AI memory of your clinic.** A web platform that turns a small Indian clinic's paper records, lab reports, patient queue and follow-up calls into one living digital brain — with a human always in control.

Built for the realities of small clinics: photos of paper instead of typing, WhatsApp instead of phone tag, and AI drafts instead of AI decisions.

---

## Why doctors use it

| The old way | With ClinicBrain |
|---|---|
| Paper prescriptions and letters pile up, get lost, can't be searched | Snap a photo — AI reads it into structured records; find anything by full-text search in seconds |
| Reading lab reports line by line, remembering last month's values by hand | Labs become rows with automatic high/low flags and per-test trend charts over months |
| Patients hover at the door asking "whose turn is it?" | Live token queue on screen; patients get a WhatsApp confirmation and a "your turn" alert |
| Staff call every patient the day before their follow-up | Automatic WhatsApp reminders 1 day before each follow-up date (consent-gated) |
| Prescribing from memory risks allergy and drug-interaction mistakes | Allergy hard-stops, interaction warnings against existing meds, max-dose checks — inline while prescribing |

**Trust principle:** the AI only drafts. Nothing enters the patient record without a human confirming it. Failed items surface in review queues — never silently dropped.

---

## What's inside

### 1. Clinic data core
- **Auth & clinics** — signup creates a clinic + first doctor account; JWT sessions; argon2 password hashing.
- **Patients** — directory with search, demographics, allergies list, WhatsApp consent flag.
- **Timeline** — every visit, prescription, lab result, note and document lands as an event on one chronological patient timeline.
- **Full-text search** — Postgres `tsvector` search across patient names and extracted document text.
- **Audit log** — append-only record of who did what, enforced at the database level.

### 2. Records digitizer
- Upload or drag any document (PDF/photo). Stored in MinIO object storage.
- Celery worker runs GPT-4o-mini vision to extract type, summary and content into a **draft**.
- Review workspace: staff confirm (→ timeline event), edit, retry, or reject drafts.
- A `fake` provider mode lets you run the whole pipeline without an API key.

### 3. Lab report reader
- Lab documents are auto-routed to a second extraction pass producing structured `{test_name, value, unit, ref_low, ref_high}` rows.
- Confirm-labs validates every value numerically (bad rows rejected with row numbers), computes flags: `normal / high / low / needs review`.
- Seeded reference of 20+ common tests; per-test **trend charts** (SVG) with reference bands.

### 4. Queue + WhatsApp follow-ups
- Check-in issues sequential token numbers per clinic per day (re-check-in returns the same active token).
- Doctor taps **Call** → patient marked in-consult → "your turn" message sent. Only one patient in consult at a time.
- Meta WhatsApp Cloud API integration behind a provider interface; `simulated` mode for demos.
- Failed sends auto-retry ×3 with exponential backoff; every message logged (`sent / retrying / failed`) on a staff dashboard.
- Hourly cron scans prescription follow-up dates and reminds patients automatically — idempotent, consent-gated.

### 5. Rx safety checker
- Drug reference seeded with 43 Indian-market drugs including max daily doses.
- **Allergy hard-stop** — blocks saving (class-level too: penicillin, sulfa, nsaid).
- **Interaction warnings** — 17 known pairs, checked within the prescription *and* against the patient's existing medications.
- **Max-dose warnings** — daily total vs reference maximum.
- Inline check while prescribing; warnings require explicit acknowledgment before save; saved prescriptions flow onto the timeline (feeding WhatsApp reminders).

### 6. Web experience
- Public landing page and photo-backed auth screens — dark-glass 3D theme, real medical imagery, animated depth effects.
- Consistent app shell across Patients, Review, Queue screens; live-polling queues and dashboards.

---

## Tech stack

- **Backend:** FastAPI · SQLAlchemy 2 (async) · Alembic · PostgreSQL (+pgvector image) · Celery + Redis · MinIO (S3) · OpenAI GPT-4o-mini · argon2 · PyJWT
- **Frontend:** React 19 · TypeScript · Vite · Tailwind CSS v3 · TanStack Query · axios · react-router
- **Quality:** 36 backend tests (pytest-asyncio, isolated test DB) · ruff lint · tsc strict builds
- **Deploy:** Docker Compose for the full stack — db, redis, minio, api, worker, beat scheduler, nginx-served frontend

## Run locally (Docker)

```bash
cp .env.example .env                 # set OPENAI_API_KEY or leave EXTRACTION_PROVIDER=fake
docker compose up -d --build         # full stack: db, redis, minio, api, worker, beat, web
docker compose exec api uv run alembic upgrade head
docker compose exec api uv run python scripts/seed_demo.py     # demo clinic + patients
docker compose exec api sh -c "PYTHONPATH=/app uv run python scripts/seed_drugs.py"   # drug reference (43 drugs)
```

Open http://localhost:5173 — demo login **`9811111111` / `demo1234`**.

Environment switches:

```bash
EXTRACTION_PROVIDER=fake    # digitizer without an OpenAI key (default fake-safe)
WHATSAPP_PROVIDER=simulated # never hits Meta; phones starting "000" simulate failures
```

Dev without Docker: see `.env.example`, then `uv run uvicorn app.main:app --port 8000` +
`uv run celery -A app.workers.celery_app worker -l info` + `uv run celery ... beat` +
`npm run dev`.

## Tests

```bash
cd backend && uv run pytest -q       # 36 tests — needs docker db/redis/minio up
cd frontend && npm run build         # tsc strict + vite production build
```

## Project structure

```
backend/
  app/routers/        auth, patients, timeline, documents, labs, queue, prescriptions, search
  app/services/       extraction providers (fake/gpt), whatsapp (simulated/meta), rx_safety rules engine, audit
  app/workers/        celery app + tasks (extract, send_whatsapp, followup reminders)
  alembic/versions/   0001–0006 migrations
  scripts/            seed_demo.py, seed_drugs.py
frontend/
  src/pages/          Landing, Login, Signup, Patients, PatientDetail, Review, Queue
  src/components/     AppShell, TrendChart, RxPanel
docs/superpowers/     design spec + phase roadmap
```

## Status

All four roadmap phases are built and tested — see `docs/superpowers/plans/2026-08-21-phase-roadmap.md`.
