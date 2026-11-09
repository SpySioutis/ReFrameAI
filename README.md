# ReFrameAI — Select it. Describe it. Reimagine it.

AI-powered video object removal & replacement studio. Upload a video, click any
object, track it across frames, and remove, replace, or restyle it with
generative AI — with temporal consistency.

> Your Video. Your Vision. Reimagined by AI.

## Features

- **Click-to-select** — pause on any frame, click an object; SAM 3.1 segments it
- **Object tracking** — optical-flow mask propagation (+ SAM video tracking when configured)
- **Remove** — video inpainting reconstructs the background, audio preserved
- **Replace / Restyle** — Muse Image generates a hero frame, composited into every frame
- **AI assistant** — Muse Spark turns plain language into structured editing plans
- **Timeline + compare** — frame-accurate seeking, mask track, before/after preview
- **EN + Ελληνικά** — full bilingual UI with persisted language switch

## Architecture

```
browser ──> Next.js 14 (frontend/) ──> FastAPI (backend/app/)
                                              ├── api/        REST + SSE
                                              ├── ai/         sam | muse_image | muse_spark | orchestration
                                              ├── video/      ffmpeg | masks | temporal | inpaint
                                              ├── services/   video | segment | edit | jobs
                                              └── SQLite (default) / Postgres, local storage / S3
```

See `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/AI_PIPELINE.md`, `docs/DEVELOPMENT.md`.

## Tech stack

- Frontend: Next.js (App Router), React, TypeScript, Tailwind, Zustand, TanStack Query, Lucide
- Backend: Python, FastAPI, Pydantic v2, SQLAlchemy, OpenCV, FFmpeg
- AI: Muse Spark 1.3, SAM 3.1, Muse Image 1.0 (Meta Model API)
- Infra: Docker Compose (Postgres, Redis), S3-compatible storage optional

## Prerequisites

- `uv` (Python env): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- `node` v18+ (+ `npm`)
- `ffmpeg` on PATH (`brew install ffmpeg`)
- Optional: `MODEL_API_KEY` from https://dev.meta.ai (SAM / Spark / Image)

## Quickstart (one click)

```bash
./start.sh            # macOS/Linux terminal
# or double-click start.command (macOS Finder) / start.bat (Windows)
```

This checks tools, installs missing deps, starts backend (:8000) + frontend (:3000),
and opens http://localhost:3000. Press Ctrl+C to stop. Logs: `data/*.log`.

Without AI credentials the app runs in **local preview mode**: upload, playback,
click-selection (classic-CV fallback), tracking, removal and export all work;
generative replace/restyle and SAM cloud segmentation need `MODEL_API_KEY`.
The UI shows an explicit warning — results are never faked.

## Manual setup

```bash
cp .env.example .env   # then edit: APP_SECRET_KEY, MODEL_API_KEY, ...

# backend
cd backend && uv sync && uv run uvicorn app.main:app --port 8000

# frontend (new terminal)
cd frontend && npm install && npm run dev
# open http://localhost:3000
```

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `APP_SECRET_KEY` | dev-secret | JWT signing (change in prod!) |
| `DATABASE_URL` | `sqlite:///./data/reframe.db` | Postgres: `postgresql+psycopg://…` |
| `REDIS_URL` | `redis://localhost:6379/0` | reserved for Celery workers |
| `MODEL_API_KEY` | _(empty)_ | Meta Model API Bearer key |
| `MODEL_API_BASE` | `https://api.meta.ai/v1` | API base |
| `S3_ENDPOINT` / `S3_BUCKET` / … | _(empty)_ | optional object storage |
| `MAX_UPLOAD_MB` / `MAX_DURATION_SEC` | 500 / 600 | upload limits |
| `STORAGE_DIR` | `./data/storage` | local asset storage |

## Docker

```bash
docker compose up --build
# frontend :3000, backend :8000, postgres :5432, redis :6379
```

## Testing

```bash
cd backend && uv run pytest -q                    # 14 tests
cd backend && uv run ruff check app tests && uv run mypy app --ignore-missing-imports
cd frontend && npx vitest run                     # 9 tests
cd frontend && npx tsc --noEmit && npx next lint && npm run build
```

## AI provider configuration

1. Create a key at https://dev.meta.ai (API keys tab, `LLM_…` format).
2. Set `MODEL_API_KEY` in `.env`, restart `./start.sh`.
3. Check **Settings → AI provider status**: all three should read *Ready*.
4. Concepts (`"red can"`) and generative edits now use the cloud APIs.

Docs used for integration (verified): `/docs/sam/overview`, `/docs/sam/segmenting`,
`/docs/sam/reading-segmentation`, `/docs/image-generation`, `/docs/muse-spark`,
`/docs/authentication`.

## Usage

1. Sign up → **New project** → upload MP4/MOV/WebM.
2. Open the project: video plays in the editor.
3. Pause, **click the object** (mask overlay appears).
4. **Track object** to propagate the mask (or skip for single-frame test).
5. Choose **Remove / Replace / Restyle**, write a prompt, **Generate**.
6. Watch progress, **Compare** original vs result, **Export** MP4.

## Deployment

- `docker compose up --build` for a single-host deploy.
- Set `APP_SECRET_KEY`, `MODEL_API_KEY`, Postgres `DATABASE_URL` in production.
- Serve the frontend behind TLS; restrict `CORS_ORIGINS` to your domain.
- For scale-out: move `job_service` to Celery+Redis (interface-compatible),
  put `STORAGE_DIR` on S3, and run workers on GPU nodes.

## Troubleshooting

- `ffmpeg not found` → `brew install ffmpeg` (export needs it).
- Backend 500 on upload → check `data/backend.log`; verify MP4/MOV/WebM + limits.
- Masks look rough in local mode → set `MODEL_API_KEY` for SAM 3.1 cloud masks.
- Generative edit fails with `not configured` → same: set `MODEL_API_KEY`.
- Port in use → `BACKEND_PORT=8001 FRONTEND_PORT=3001 ./start.sh`.

## Known limitations

- Local-mode segmentation is GrabCut-based (rough edges); SAM cloud is precise.
- Replace/restyle composites ONE hero image across frames (motion-followed) —
  per-frame generation would flicker; true video-diffusion is future work.
- No ProPainter yet: removal is OpenCV Telea inpainting (good for small objects).
- WebM uploads are accepted but SAM cloud requires MP4/MOV (auto-remux on export path only).
- Max 16 tracked objects per SAM request (API limit).

## License

MIT — see `LICENSE`.
