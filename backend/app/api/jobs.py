import asyncio
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from ..db import SessionLocal, get_db
from ..models import EditingJob, User
from ..schemas import JobOut
from ..services import job_service
from .deps import current_user

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _out(job: EditingJob) -> JobOut:
    return JobOut(id=job.id, job_type=job.job_type, status=job.status,
                  progress=job.progress, error_message=job.error_message or "",
                  metadata=job.job_metadata or {})


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = db.get(EditingJob, job_id)
    if not job or (job.project and job.project.user_id != user.id):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="job not found")
    return _out(job)


@router.post("/{job_id}/cancel")
def cancel(job_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    job = db.get(EditingJob, job_id)
    if not job or (job.project and job.project.user_id != user.id):
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="job not found")
    job_service.cancel_job(job_id)
    if job.status in ("queued", "running"):
        job.status = "cancelled"
        db.commit()
    return {"ok": True}


@router.get("/{job_id}/events")
async def job_events(job_id: str):
    async def _gen():
        while True:
            db = SessionLocal()
            try:
                job = db.get(EditingJob, job_id)
                if not job:
                    yield {"event": "error", "data": json.dumps({"detail": "job not found"})}
                    return
                yield {"event": "progress", "data": json.dumps({
                    "status": job.status, "progress": job.progress,
                    "error": job.error_message or "", "metadata": job.job_metadata or {}})}
                if job.status in ("done", "failed", "cancelled"):
                    return
            finally:
                db.close()
            await asyncio.sleep(0.7)

    return EventSourceResponse(_gen())
