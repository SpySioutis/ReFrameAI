#!/bin/bash
# ReFrameAI — one-click starter (macOS / Linux).
# Starts backend (FastAPI) + frontend (Next.js), opens the browser.
set -u
cd "$(dirname "$0")"

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
API_URL="http://localhost:${BACKEND_PORT}"
APP_URL="http://localhost:${FRONTEND_PORT}"

fail() { echo "ERROR: $1" >&2; exit 1; }

# 1. Required tools
command -v uv >/dev/null 2>&1 || fail "uv is required. Install: curl -LsSf https://astral.sh/uv/install.sh | sh"
command -v node >/dev/null 2>&1 || fail "node is required. Install: https://nodejs.org (v18+)"
command -v npm >/dev/null 2>&1 || fail "npm is required (ships with node)."
command -v ffmpeg >/dev/null 2>&1 || echo "WARNING: ffmpeg not found — video export will fail. Install: brew install ffmpeg"

# 2. Env file
if [ ! -f .env ] && [ -f .env.example ]; then
  echo "Creating .env from .env.example (edit it to add MODEL_API_KEY)…"
  cp .env.example .env
fi
# shellcheck disable=SC1091
[ -f .env ] && set -a && . ./.env && set +a || true
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-3000}"
API_URL="http://localhost:${BACKEND_PORT}"
APP_URL="http://localhost:${FRONTEND_PORT}"

# 3. Install dependencies only if missing
if [ ! -d backend/.venv ]; then
  echo "Installing backend dependencies (first run)…"
  (cd backend && uv sync) || fail "backend install failed"
fi
if [ ! -d frontend/node_modules ]; then
  echo "Installing frontend dependencies (first run)…"
  (cd frontend && npm install --no-audit --no-fund) || fail "frontend install failed"
fi

mkdir -p data/storage

# 4. Start services
echo "Starting backend on ${API_URL} …"
(cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port "${BACKEND_PORT}" > ../data/backend.log 2>&1 & echo $! > ../data/backend.pid)
echo "Starting frontend on ${APP_URL} …"
(cd frontend && NEXT_PUBLIC_API_URL="" FRONTEND_PORT="${FRONTEND_PORT}" npm run dev > ../data/frontend.log 2>&1 & echo $! > ../data/frontend.pid)

cleanup() {
  echo ""
  echo "Shutting down…"
  [ -f data/backend.pid ] && kill "$(cat data/backend.pid)" 2>/dev/null || true
  [ -f data/frontend.pid ] && kill "$(cat data/frontend.pid)" 2>/dev/null || true
  # Also kill child processes spawned by npm
  pkill -P "$(cat data/frontend.pid 2>/dev/null)" 2>/dev/null || true
  rm -f data/backend.pid data/frontend.pid
  exit 0
}
trap cleanup INT TERM

# 5. Wait for readiness, then open browser
echo "Waiting for services…"
for i in $(seq 1 60); do
  if curl -sf "${API_URL}/api/health" >/dev/null 2>&1; then break; fi
  sleep 1
done
curl -sf "${API_URL}/api/health" >/dev/null 2>&1 || echo "WARNING: backend not responding yet (see data/backend.log)"
for i in $(seq 1 60); do
  if curl -sf "${APP_URL}" >/dev/null 2>&1; then break; fi
  sleep 1
done
echo "ReFrameAI is ready: ${APP_URL}"
if command -v open >/dev/null 2>&1; then open "${APP_URL}"; elif command -v xdg-open >/dev/null 2>&1; then xdg-open "${APP_URL}"; fi
echo "Logs: data/backend.log, data/frontend.log — Press Ctrl+C to stop."

# 6. Stay alive until Ctrl+C
while true; do sleep 1; done
