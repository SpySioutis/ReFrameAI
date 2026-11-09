# ARCHITECTURE.md

## Overview

ReFrameAI is a monorepo SaaS MVP:

- `frontend/` — Next.js 14 App Router, dark-mode editor UI (EN+EL).
- `backend/` — FastAPI service: REST API, video pipeline, AI providers, jobs.
- `docker-compose.yml` — Postgres + Redis + backend + frontend for production-like deploys.
- Local dev needs **zero infra**: SQLite + filesystem storage + in-process jobs.

```
┌─────────┐  /api/*   ┌──────────┐  SQLAlchemy  ┌─────────┐
│ Next.js │ ────────> │ FastAPI  │ ───────────> │ SQLite/ │
│  :3000  │ <video/   │  :8000   │              │ Postgres│
└─────────┘  blob     └────┬─────┘              └─────────┘
                           │ storage keys            │
                    ┌──────┴──────┐           ┌──────┴──────┐
                    │ data/storage│           │ Meta API    │
                    │ (or S3)     │           │ sam/spark/  │
                    └─────────────┘           │ image       │
                                              └─────────────┘
```

## Backend modules

| Path | Responsibility |
|---|---|
| `app/main.py` | FastAPI factory, CORS, routers, health |
| `app/api/` | `auth`, `projects`, `videos`, `objects`, `editing`, `jobs` (SSE), `assistant`, `providers` |
| `app/core/` | `config` (env), `security` (bcrypt+JWT), `storage` (local/S3 keys), `providers` (states) |
| `app/db.py` | engine/session, `init_db()` (SQLite file or Postgres) |
| `app/models/` | User, Project, VideoAsset, DetectedObject, SegmentationMask, EditingJob, EditingOperation |
| `app/video/` | `ffmpeg` (probe/extract/export), `masks`, `temporal` (optical flow), `inpaint` (remove/composite) |
| `app/ai/sam/` | `provider` (Responses API + Files upload), `parser` (wire grammar), `prompts`, `local` (GrabCut fallback) |
| `app/ai/muse_image/` | `provider` (`/images/generations`, `/images/edits` JSON) |
| `app/ai/muse_spark/` | `provider` (chat-completions planning + chat, local fallback) |
| `app/ai/orchestration/` | allowlisted `tools` with Pydantic arg schemas |
| `app/services/` | `video_service`, `segment_service`, `edit_service`, `job_service` |
| `app/workers/` | production worker notes (MVP runs in-process) |

## Request flows

**Upload**: `POST video` → stream to `projects/{id}/source.*` → `probe_video` →
thumbnail → project row updated. Limits enforced (format/size/duration).

**Segment**: frontend converts click → source px (`lib/coordinates.ts`) →
`POST objects/segment` → SAM cloud (`input_image` data URL, object prompt) or
local GrabCut → mask PNG stored → `DetectedObject` + `SegmentationMask` rows.

**Track**: `POST objects/track` → background `run_track` (optical-flow
propagation, sampled commits) → progress via `GET jobs/{id}` or SSE.

**Remove**: `run_remove` → per-frame inpaint over stored/propagated masks →
`frames_to_video` (+faststart, audio mux) → `VideoAsset(result)`.

**Replace/restyle**: hero keyframe crop → Muse Image `/images/edits` →
motion-followed feathered composite across frames → encode + mux audio.

**Assistant**: `POST assistant/chat` → Spark plan (cloud or rule-based) →
reply + structured plan + suggested tool. Tools validated via registry.

## Auth & security

- Bcrypt passwords, JWT Bearer tokens (7-day expiry), per-project ownership checks.
- `MODEL_API_KEY` server-side only; frontend talks to same-origin `/api` (Next rewrites).
- Upload validation (ext/mime/size/duration); storage keys are traversal-safe.
- No secrets in repo (`.env` gitignored, `.env.example` documented).

## Scaling path

- `job_service` → Celery + Redis (same job-row contract, SSE unchanged).
- SQLite → Postgres (`DATABASE_URL`), local storage → S3 mirror.
- Workers on GPU nodes; `max_workers` caps concurrency; retries with backoff.
- Previews stay low-res; final exports use full-res + CRF 18.
