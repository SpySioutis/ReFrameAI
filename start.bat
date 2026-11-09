@echo off
REM ReFrameAI — one-click starter (Windows). Double-click to run.
cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
  echo ERROR: uv is required. Install: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  pause
  exit /b 1
)
where node >nul 2>nul
if errorlevel 1 (
  echo ERROR: node is required. Install: https://nodejs.org (v18+^)
  pause
  exit /b 1
)
where ffmpeg >nul 2>nul
if errorlevel 1 echo WARNING: ffmpeg not found - video export will fail. Install: winget install ffmpeg

if not exist .env (
  if exist .env.example (
    echo Creating .env from .env.example (edit it to add MODEL_API_KEY^)…
    copy .env.example .env >nul
  )
)

if not exist backend\.venv (
  echo Installing backend dependencies (first run^)…
  cd backend
  uv sync || ( echo Backend install failed & pause & exit /b 1 )
  cd ..
)
if not exist frontend\node_modules (
  echo Installing frontend dependencies (first run^)…
  cd frontend
  call npm install --no-audit --no-fund || ( echo Frontend install failed & pause & exit /b 1 )
  cd ..
)

if not exist data\storage mkdir data\storage

echo Starting backend on http://localhost:8000 …
start "ReFrameAI backend" /min cmd /c "cd backend && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000"
echo Starting frontend on http://localhost:3000 …
start "ReFrameAI frontend" /min cmd /c "cd frontend && npm run dev"

echo Waiting for services…
timeout /t 8 /nobreak >nul
start "" "http://localhost:3000"
echo ReFrameAI is ready: http://localhost:3000
echo To stop: close the "ReFrameAI backend" and "ReFrameAI frontend" windows.
pause
