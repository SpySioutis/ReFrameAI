"""ReFrameAI backend — FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import assistant, auth, editing, jobs, objects, projects, providers, videos
from .core.config import get_settings
from .db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="ReFrameAI", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ValueError)
    async def _value_error(request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc), "code": "bad_request"})

    @app.get("/api/health")
    def health():
        return {"ok": True, "ai_configured": settings.ai_configured, "env": settings.app_env}

    app.include_router(auth.router)
    app.include_router(projects.router)
    app.include_router(videos.router)
    app.include_router(objects.router)
    app.include_router(editing.router)
    app.include_router(jobs.router)
    app.include_router(assistant.router)
    app.include_router(providers.router)
    return app


app = create_app()
