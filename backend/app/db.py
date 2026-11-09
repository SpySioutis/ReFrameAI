"""SQLAlchemy engine/session. SQLite by default, Postgres when DATABASE_URL is postgres."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .core.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():  # type: ignore[no-untyped-def]
    settings = get_settings()
    url = settings.database_url
    if url.startswith("sqlite"):
        # Ensure parent dir exists for file-based sqlite.
        path = url.replace("sqlite:///", "")
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(url, connect_args={"check_same_thread": False}, future=True)
    return create_engine(url, future=True, pool_pre_ping=True)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from . import models  # noqa: F401  (register models)

    Base.metadata.create_all(bind=engine)
