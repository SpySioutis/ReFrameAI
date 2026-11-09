# AGENTS.md — ReFrameAI

## Stack
- Backend: Python 3.11+ (uv), FastAPI, SQLAlchemy 2, Pydantic v2, OpenCV, FFmpeg
- Frontend: Next.js 14 App Router, React 18, TypeScript, Tailwind, Zustand, TanStack Query
- DB: SQLite default (`./data/reframe.db`), Postgres via `DATABASE_URL`
- Jobs: in-process ThreadPoolExecutor (`app/services/job_service.py`); Redis/Celery later
- AI: Meta Model API (`https://api.meta.ai/v1`, Bearer `MODEL_API_KEY`): `sam-3.1`, `muse-spark-1.3`, `muse-image-1.0`

## Commands
- Start all: `./start.sh` (or double-click `start.command` / `start.bat`)
- Backend dev: `cd backend && uv run uvicorn app.main:app --port 8000`
- Frontend dev: `cd frontend && npm run dev`
- Backend tests: `cd backend && uv run pytest -q`
- Frontend tests: `cd frontend && npx vitest run`
- Typecheck: `cd backend && uv run mypy app --ignore-missing-imports` / `cd frontend && npx tsc --noEmit`
- Lint: `cd backend && uv run ruff check app tests` / `cd frontend && npx next lint`
- Build: `cd frontend && npm run build`

## Structure
- `backend/app/api/` REST routes (auth, projects, videos, objects, editing, jobs, assistant, providers)
- `backend/app/ai/{sam,muse_image,muse_spark,orchestration}/` AI providers + tool registry
- `backend/app/video/` ffmpeg/frames/masks/temporal/inpaint pipelines
- `backend/app/services/` video/job/segment/edit orchestration; `backend/tests/` pytest
- `frontend/app/` pages (landing, dashboard, editor/[projectId], settings, auth)
- `frontend/components/editor/` VideoStage/Timeline/Assistant; `frontend/lib/` i18n + coordinates
- `frontend/locales/{en,el}.json` i18n strings; `frontend/stores/` zustand auth+editor

## Conventions
- i18n: no hardcoded UI strings — use `t("...")` + both locale files; EN fallback
- Coordinates: screen→video mapping lives in `lib/coordinates.ts` (tested); never assume 1:1
- AI: providers return explicit states; never fake results; local fallback labeled `provider="local"`
- Secrets: never commit `.env`; keys only via env (`MODEL_API_KEY`)
- Git: meaningful commits per milestone; never force-push; remote `origin` — push only if asked

## Definition of done
- Compliance with `/SKILLS.md` Rules 1–5 + Milestones 1–6 of the master prompt
- `pytest` 14/14, `vitest` 9/9, `tsc`, `mypy`, `ruff`, `next lint`, `next build` all green
- Smoke test: register → project → upload → play → click-select → track → remove → export MP4
