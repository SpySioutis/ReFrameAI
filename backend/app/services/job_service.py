"""Background job runner (in-process ThreadPoolExecutor).

Interface-compatible with a future Celery/Redis worker: jobs are rows in
`editing_jobs`, progress is polled via GET /api/jobs/{id} and streamed via SSE.
CPU/GPU-heavy work never runs inside the request handler.
"""

from __future__ import annotations

import traceback
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

from ..db import SessionLocal, init_db
from ..models import EditingJob

_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="reframe-job")
_cancelled: set[str] = set()


def cancel_job(job_id: str) -> None:
    _cancelled.add(job_id)


def is_cancelled(job_id: str) -> bool:
    return job_id in _cancelled


def update_job(job_id: str, *, status: str | None = None, progress: float | None = None,
               error: str = "", metadata: dict | None = None) -> None:
    init_db()
    db = SessionLocal()
    try:
        job = db.get(EditingJob, job_id)
        if not job:
            return
        if status:
            job.status = status
        if progress is not None:
            job.progress = max(0.0, min(1.0, float(progress)))
        if error:
            job.error_message = error[:2000]
        if metadata is not None:
            job.job_metadata = {**(job.job_metadata or {}), **metadata}
        if status in ("done", "failed", "cancelled"):
            job.completed_at = datetime.now(UTC)
        db.commit()
    finally:
        db.close()


def submit(job_id: str, fn: Callable[[], None]) -> None:
    def _wrap() -> None:
        if is_cancelled(job_id):
            update_job(job_id, status="cancelled")
            return
        update_job(job_id, status="running", progress=0.0)
        try:
            fn()
            if is_cancelled(job_id):
                update_job(job_id, status="cancelled")
            else:
                update_job(job_id, status="done", progress=1.0)
        except Exception as e:
            update_job(job_id, status="failed", error=f"{type(e).__name__}: {e}\n{traceback.format_exc()[-1500:]}")

    update_job(job_id, status="queued", progress=0.0)
    _executor.submit(_wrap)
