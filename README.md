# ClinicBrain

The AI memory of the clinic. Phase 1: data core + records digitizer.

## Run locally (Docker)

```bash
cp .env.example .env
docker compose up -d db redis minio minio-init
cd backend && uv sync && uv run alembic upgrade head && uv run scripts/seed_demo.py
uv run uvicorn app.main:app --port 8000
uv run celery -A app.workers.celery_app:celery_app worker -l info   # second terminal
cd ../frontend && npm install && npm run dev                        # third terminal
```

Open http://localhost:5173 — demo login `9811111111` / `demo1234`.

Set `EXTRACTION_PROVIDER=fake` to test the digitizer without an OpenAI key.
With a key, GPT-4o-mini vision extracts real documents; every extraction is a
draft requiring human confirmation before it reaches the timeline.

## Tests

```bash
cd backend && uv run pytest -q     # 16 tests, needs docker db/redis/minio up
cd frontend && npm run build       # tsc + vite production build
```

## Phase status

- Phase 1 (this repo state): auth, patients, timeline, upload → AI extract → review → timeline, full-text search, audit log.
- Phases 2–4 (lab reader, WhatsApp queue, rx safety): see `docs/superpowers/plans/2026-08-21-phase-roadmap.md`.
