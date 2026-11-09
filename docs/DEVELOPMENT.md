# DEVELOPMENT.md

## Setup

```bash
cp .env.example .env
cd backend && uv sync
cd frontend && npm install
./start.sh   # or run backend/frontend manually (see README)
```

## Migrations

MVP: `Base.metadata.create_all()` on startup (`app/db.py::init_db`).
`backend/migrations/0001_initial.py` snapshots the 7 tables.
Production: introduce Alembic `env.py` against the same models before first
prod deploy; do not hand-edit the snapshot.

## Tests

```bash
cd backend && uv run pytest -q                 # 14: SAM parser/prompts, tools, planner, masks, API
cd frontend && npx vitest run                  # 9: coordinates mapping, i18n EN/EL parity
```

External AI is mocked/absent in tests (`MODEL_API_KEY=""`): SAM parser tests use
golden wire strings; API tests assert `not_configured` states and local planner.

## Checks (all must pass)

```bash
cd backend && uv run ruff check app tests && uv run mypy app --ignore-missing-imports
cd frontend && npx tsc --noEmit && npx next lint && npm run build
bash -n start.sh && bash -n start.command
```

## Smoke test (end-to-end)

```bash
./start.sh &
# register in UI, create project, upload video (or use script below)
```

Scripted API smoke (creates synthetic video, segments, tracks, removes, exports):

```bash
cd backend && uv run python - <<'EOF'
# see infrastructure/scripts/smoke.py
EOF
```

Or run `uv run python ../infrastructure/scripts/smoke.py` from `backend/`.

## i18n

- Strings in `frontend/locales/en.json` + `el.json`; access via `t("a.b.c")`.
- `lib/i18n.test.ts` enforces key parity; EN is the fallback (never blank).
- Switch in header (`LanguageSwitch`) + Settings radio; persisted in localStorage.

## Conventions

- Backend: ruff (line-length 100), mypy strict-ish, `from __future__ import annotations`.
- Frontend: `use client` for interactive components; server components where static.
- Never log or return `MODEL_API_KEY`; mask keys in errors (upstream excerpts truncated).
- Never commit `data/`, `.env`, videos, or weights.
