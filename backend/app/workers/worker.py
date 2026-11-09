"""Backward-compat worker entrypoint.

Local dev runs jobs in-process via services.job_service (ThreadPoolExecutor).
This module documents the production path: run one or more worker processes
with Redis/Celery. For the MVP it simply confirms the job system imports.
"""

from __future__ import annotations


def main() -> None:
    from app.db import init_db

    init_db()
    print("ReFrameAI worker: in-process job runner active (see services.job_service).")
    print("For production, configure REDIS_URL and run celery workers (docs/ARCHITECTURE.md).")


if __name__ == "__main__":
    main()
