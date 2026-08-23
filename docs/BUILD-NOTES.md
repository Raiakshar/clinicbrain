# ClinicBrain — Build Notes (First to Last)

How the whole platform was conceived, built, tested, debugged and deployed — written so you can re-read and understand every part later.

---

## 1. What ClinicBrain is

A web platform that becomes **"the AI memory"** of a small Indian clinic:

- Reception snaps photos of paper records → AI reads them into structured drafts.
- Lab reports become rows with normal/high/low flags and trend charts over time.
- Patients get WhatsApp updates: queue token, "your turn", follow-up reminders.
- Doctors get safety guardrails while prescribing (allergies, interactions, max dose).

**Core trust rule (used everywhere):** the AI only *drafts*. Nothing enters the patient record until a human confirms it. Failures are never silent — they show up on dashboards.

---

## 2. The plan

We wrote a 4-phase roadmap first (`docs/superpowers/plans/2026-08-21-phase-roadmap.md`) and a full design spec (`docs/superpowers/specs/2026-08-21-clinicbrain-design.md`), then built one phase at a time, each ending with tests green + live verification + a git commit.

| Phase | What ships |
|---|---|
| 1 | Data core: auth, clinics, patients, timeline, document digitizer pipeline, search, audit log |
| 2 | Lab report reader: extraction → validation → confirm → trends |
| 3 | Queue tokens + WhatsApp follow-ups with retries and reminders |
| 4 | Rx safety checker: allergy blocks, interactions, max-dose |

---

## 3. Architecture (how the pieces fit)

```
Browser (React + Tailwind)
   │ axios, JWT bearer token
   ▼
nginx (serves frontend + proxies /api)
   ▼
FastAPI (backend/app)  ──►  PostgreSQL (patients, docs, labs, queue, rx, audit)
   │                            ▲
   │ enqueues jobs              │
   ▼                            │
Redis broker ──► Celery workers ─┘ (extraction, WhatsApp sends, reminders)
   ▲
   └── Celery beat (hourly scheduler for follow-up reminders)

MinIO (S3-compatible) stores uploaded documents/photos.
```

Key idea: **the API never does slow work** (AI calls, sending messages). It writes a row and enqueues a Celery task; workers do the work and update the database. The frontend polls every few seconds so screens feel live.

---

## 4. Phase 1 — Data core & digitizer (how it works)

1. **Signup/login**: one signup creates clinic + doctor. Passwords hashed with argon2; API returns a JWT; frontend stores it and sends `Authorization: Bearer ...` on every call.
2. **Patients & timeline**: patients belong to a clinic. Every event type (visit, prescription, lab, note, document) is a row in `timeline_events` with a JSONB payload — one timeline per patient.
3. **Digitizer flow** (the heart of Phase 1):
   - Upload file → saved to MinIO, `documents` row created with status `pending`.
   - Celery task downloads bytes → sends to provider (`gpt` = GPT-4o-mini vision, or `fake` for demos) → gets `{document_type, summary, content_text}`.
   - Status moves `pending → processing → needs_review` (or `failed` with error text).
   - Staff open Review page → confirm → status `processed` + timeline event created. Reject deletes. Retry re-enqueues.
4. **Search**: Postgres generated `tsvector` columns + GIN index; search matches patient names and extracted document text.
5. **Audit log**: append-only table; a DB trigger prevents UPDATE/DELETE — even admins can't rewrite history.

---

## 5. Phase 2 — Lab reader (how it works)

- When extraction sees `document_type == "lab"`, it automatically chains a second AI pass asking for structured rows: `{test_name, value, unit, ref_low, ref_high}`.
- **Confirm-labs endpoint validates like a human would**: each value must be a clean number (regex strips commas/units). Bad row → HTTP 422 saying exactly which row failed. Good rows get flags computed by comparing against reference range → `normal/high/low/review`.
- Confirmed rows go into `lab_results`; a timeline event is added.
- Trend endpoint returns one test's values over time → frontend draws an SVG chart with dashed reference-range lines and flag-colored dots.

---

## 6. Phase 3 — Queue + WhatsApp (how it works)

- **Check-in**: receptionist searches by name/phone, or uses "+ New patient". Backend assigns token number = max(today's numbers)+1 per clinic per day. Checking in again returns the same active token (no duplicates). Walk-ins with an existing phone number reuse that patient.
- **Call**: only allowed if nobody else is `in_consult` (else HTTP 409). Sets status, sends "your turn" WhatsApp.
- **WhatsApp design**: a `whatsapp_log` row is created first (status `retrying`), then a Celery task tries to send.
  - Provider interface: `simulated` (default; phones starting `000` fail — great for testing) or Meta Cloud Graph API.
  - Task has `autoretry_for=(Exception,), retry_backoff=True, max_retries=3` → exponential waits between tries → ends `sent` or `failed` with the error stored.
  - Dashboard shows every message + retry counts + errors.
- **Consent (DPDP)**: if `patient.whatsapp_consent` is false, no message is ever created.
- **Follow-up reminders**: Celery beat runs hourly; scans prescription events whose payload `followup_date` equals today+clinic's reminder offset; skips if a reminder log already exists (idempotent); otherwise queues the send.

---

## 7. Phase 4 — Rx safety (how it works)

- `drug_reference`: 43 Indian-market drugs seeded with generic name, class, max daily dose.
- Patient allergies are class-aware strings: typing `penicillin` blocks all penicillin-class drugs; `sulfa` blocks sulfonamides.
- Rules engine (`app/services/rx_safety.py`):
  - **Allergy match → hard BLOCK** (save returns HTTP 400, always).
  - **Interactions → warning** (17 known pairs like Warfarin+Aspirin, Clopidogrel+Omeprazole). Checked two ways: within the new prescription AND against drugs in the patient's existing prescriptions.
  - **Max dose → warning** when dose × frequency/day exceeds reference.
- Save flow: blocks → reject outright. Warnings → HTTP 409 until doctor ticks "I acknowledge the warnings".
- Saving creates prescription + items + a timeline event carrying optional `followup_date` — which feeds Phase 3 reminders automatically.

---

## 8. Frontend structure (how UI is organized)

- `AppShell` — shared glass navbar (Patients / Review / Queue pills, user chip, logout) + animated background orbs; every app page wraps itself in it.
- `Landing.tsx` — public marketing page ("/") with real medical imagery, tilting 3D hero collage, floating stat chips.
- Dark-glass design system lives in `src/index.css` utilities: `.cb-card`, `.cb-input`, `.cb-btn`, `.cb-chip`, `.text-gradient`, plus keyframes (floaty, orb, glow).
- Data fetching is TanStack Query everywhere with short refetch intervals (queues feel real-time).
- `RxPanel` (patient detail Rx tab): allergy chips editor, drug autocomplete with reference info, items list, live debounced safety check, acknowledge-to-save, history list.

---

## 9. Debugging war stories (what broke and how we fixed it)

These teach the most:

1. **Port conflicts**: local Homebrew Postgres squats 5432 → Docker DB mapped to 5433; another container held port 8000 → API moved to other host ports (nginx talks to `api:8000` inside the Docker network anyway).
2. **Celery cross-event-loop crash (Phase 2)**: asyncpg connections created in one asyncio loop crashed when reused in another. Fix: workers build a **fresh NullPool engine + sessionmaker per task run**, disposed after.
3. **Silent task loss (Phase 3)**: messages published but never processed. Root cause: Celery publishes to its default queue named `celery`, while our worker listened on `-Q default`. Fix: set `task_default_queue = "default"` in the Celery app config. Lesson: **always pin the queue name explicitly**.
4. **Stale worker after code changes**: an old worker process didn't know new tasks → "Received unregistered task of type 'whatsapp.send'". Fix: kill all celery processes and restart; later switched pool to `--pool=solo` locally for reliability.
5. **NULL breaks strict schemas**: seeded patients had no consent value → response validation error. Fix: make response fields nullable (`bool | None`) instead of lying with defaults.
6. **Blank white page in production**: React crashed at mount because `AuthProvider` called `useNavigate()` **outside** `<BrowserRouter>`. tsc couldn't catch it. We reproduced headlessly with jsdom executing the real bundle → got the exact stack (`useNavigateUnstable → invariant`). Lesson: render-order context bugs need runtime reproduction.
7. **Docker bind-mount ate the Linux venv**: mounting `./backend:/app` overwrote the image's venv with macOS paths → uvicorn crashed on boot. Fix: anonymous volume shield `"/app/.venv"` alongside the bind mount.
8. **Tunnel flakiness**: cloudflared quick tunnels die on network blips and QUIC was unreachable → restart with `--protocol http2` (TCP/443). Quick tunnels get a NEW URL each restart.

---

## 10. Testing approach (why we trust it)

- `tests/conftest.py` creates an isolated `clinicbrain_test` DB, applies migrations-equivalent schema (`create_all` + raw DDL for search columns), truncates between tests, seeds the drug reference, overrides auth/storage dependencies, and stubs Celery `.delay()` so tests never need Redis.
- Tests cover: auth, patient scoping by clinic, upload→extract→confirm, search, lab validation failures (row-level), flags, queue numbering/dedup/call-guard, walk-in matching, WhatsApp retry→failed paths, reminder idempotency, allergy hard-block, interaction (same-Rx + cross-prescription), max-dose ack gate, followup_date propagation. **39 passing.**
- Every phase also got a **live E2E through real HTTP** before committing (real worker, real MinIO, simulated providers).

## 11. Deployment (how it's served)

- `docker compose up -d --build` brings up db, redis, minio (+bucket init with retry), api, worker, beat, web(nginx).
- Migrations/seeds run via `docker compose exec`.
- Public access: cloudflared quick tunnel → `https://<random>.trycloudflare.com` (no account; URL rotates on restart; tied to the local machine). Production path later: Fly.io / Render / any Docker host.
- Demo login: `9811111111` / `demo1234`.

## 12. Where everything lives

```
docs/superpowers/
  specs/2026-08-21-clinicbrain-design.md      original product spec
  plans/2026-08-21-phase-roadmap.md           roadmap with build log per phase
backend/app/routers/                          auth, patients, timeline, documents,
                                              labs, queue, prescriptions, search
backend/app/services/                         extraction (fake|gpt), whatsapp (simulated|meta),
                                              rx_safety rules engine, audit
backend/app/workers/tasks.py                  extract tasks, send_whatsapp, reminders
backend/scripts/                              seed_demo.py, seed_drugs.py
frontend/src/pages/                           Landing, Login, Signup, Patients,
                                              PatientDetail, Review, Queue
frontend/src/components/                      AppShell, TrendChart, RxPanel
```
