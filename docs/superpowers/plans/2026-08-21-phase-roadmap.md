# ClinicBrain — Phase Roadmap

**Source spec:** `docs/superpowers/specs/2026-08-21-clinicbrain-design.md`
**Rule:** One implementation plan per phase. Each phase ends deployable and demoable. Next phase's plan is written only after the previous phase is done (its interfaces become concrete).

## Phase 1 — Data Core + Records Digitizer ✅ planned
Foundation everything else shares: clinics/users/auth, patients, `timeline_events`, document upload, AI extraction draft → human confirm → timeline. Searchable history.

Build strategy (approved): **walking skeleton first** — thin end-to-end slice before depth, so integration risk surfaces in week one and the product is demoable early. "Done" = builds properly and runs via docker compose.

Milestones:
1. **M0 — Scaffold:** monorepo `backend/` (FastAPI) + `frontend/` (Vite + React + Tailwind); compose with postgres+pgvector, redis, api, worker, web; pytest + lint wired up.
2. **M1 — Walking skeleton:** clinic signup/login (JWT + argon2) → create/list patients → manual timeline note → visible on patient timeline page. Whole stack runs with `docker compose up`.
3. **M2 — Digitizer pipeline:** upload → object storage (MinIO locally / R2 in prod, same S3 API) → Celery job → GPT-4o-mini vision extraction → **draft** → staff review/edit/confirm → `timeline_events` row. Failed extractions land in a review queue with retry. Extraction provider behind an interface.
4. **M3 — Search + trust polish:** Postgres full-text search over OCR text + timeline events (pgvector installed, semantic search deferred). Audit log on every clinical read/write. Unit tests (validators), API integration tests, one E2E test (upload → confirm → on timeline).

Deferred out of Phase 1: Gemini fallback activation (interface ready), golden-set accuracy scoring (awaits partner clinic photos), multi-clinic admin UI.

**Plan:** `docs/superpowers/plans/2026-08-21-phase1-data-core-records-digitizer.md`

## Phase 2 — Lab Report Reader
Photo → structured `{test_name, value, unit, ref_low, ref_high}` rows → regex validation → draft table → confirm → `lab_results` → trend charts. Reuses Phase 1 upload/draft/confirm pipeline with a new extractor.
**Plan:** written after Phase 1 completes.

## Phase 3 — Queue + WhatsApp Follow-ups
`queue_tokens` flow (issue → confirm → "your turn"), Meta WhatsApp Cloud API integration with retry/backoff + `whatsapp_log`, cron reminder 1 day before `followup_date`.
**Plan:** written after Phase 2 completes.

## Phase 4 — Rx Safety Checker
`drug_reference` seed data, rules engine (allergy hard-block, interaction warning, max-dose warning) + inline API while prescribing; prescription UI with warnings before save.
**Plan:** written after Phase 3 completes.
