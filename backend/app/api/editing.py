from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..core.storage import get_storage
from ..db import get_db
from ..models import DetectedObject, EditingJob, EditingOperation, User, VideoAsset
from ..schemas import EditRequest, ExportRequest, JobOut
from ..services import edit_service, job_service
from .deps import current_user, owned_project

router = APIRouter(prefix="/api/projects/{project_id}", tags=["editing"])


def _job_out(job: EditingJob) -> JobOut:
    return JobOut(id=job.id, job_type=job.job_type, status=job.status,
                  progress=job.progress, error_message=job.error_message or "",
                  metadata=job.job_metadata or {})


def _start_edit(project_id: str, operation: str, body: EditRequest, db: Session) -> JobOut:
    if operation in ("replace", "restyle") and not body.prompt.strip():
        raise HTTPException(status_code=400, detail="a prompt is required")
    if body.object_id:
        obj = db.get(DetectedObject, body.object_id)
        if not obj or obj.project_id != project_id:
            raise HTTPException(status_code=404, detail="object not found")
        db.add(EditingOperation(project_id=project_id, object_id=body.object_id,
                                operation_type=operation, prompt=body.prompt,
                                parameters={"strength": body.strength}))
    job = EditingJob(project_id=project_id, job_type=operation, status="queued",
                     job_metadata={"object_id": body.object_id or "", "prompt": body.prompt[:500]})
    db.add(job)
    db.commit()
    db.refresh(job)
    if operation == "remove":
        assert body.object_id, "object_id required for removal"
        oid = body.object_id
        job_service.submit(job.id, lambda: edit_service.run_remove(job.id, project_id, oid, body.preserve_audio))
    else:
        assert body.object_id, "object_id required"
        oid, prompt, op = body.object_id, body.prompt, operation
        job_service.submit(job.id, lambda: edit_service.run_replace(job.id, project_id, oid, prompt, op, body.preserve_audio))
    return _job_out(job)


@router.post("/edit/remove", response_model=JobOut)
def edit_remove(project_id: str, body: EditRequest,
                user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    if not project.source_video:
        raise HTTPException(status_code=400, detail="upload a video first")
    if not body.object_id:
        raise HTTPException(status_code=400, detail="object_id is required")
    return _start_edit(project_id, "remove", body, db)


@router.post("/edit/replace", response_model=JobOut)
def edit_replace(project_id: str, body: EditRequest,
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    if not project.source_video:
        raise HTTPException(status_code=400, detail="upload a video first")
    if not body.object_id:
        raise HTTPException(status_code=400, detail="object_id is required")
    return _start_edit(project_id, "replace", body, db)


@router.post("/edit/restyle", response_model=JobOut)
def edit_restyle(project_id: str, body: EditRequest,
                 user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    if not project.source_video:
        raise HTTPException(status_code=400, detail="upload a video first")
    if not body.object_id:
        raise HTTPException(status_code=400, detail="object_id is required")
    return _start_edit(project_id, "restyle", body, db)


@router.get("/history")
def history(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_project(project_id, user, db)
    ops = db.query(EditingOperation).filter(EditingOperation.project_id == project_id).order_by(EditingOperation.created_at.desc()).all()
    return [{"id": o.id, "operation": o.operation_type, "prompt": o.prompt,
             "object_id": o.object_id, "created_at": o.created_at.isoformat() if o.created_at else ""} for o in ops]


@router.post("/export", response_model=JobOut)
def export(project_id: str, body: ExportRequest,
           user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    # Export = the latest successful result asset (or source if no edits yet).
    latest = db.query(VideoAsset).filter(VideoAsset.project_id == project_id,
                                        VideoAsset.asset_type == "result").order_by(VideoAsset.created_at.desc()).first()
    src_key = latest.storage_path if latest else project.source_video
    if not src_key:
        raise HTTPException(status_code=400, detail="nothing to export yet")
    job = EditingJob(project_id=project_id, job_type="export", status="done", progress=1.0,
                     job_metadata={"result": src_key, "quality": body.quality})
    from datetime import datetime

    job.completed_at = datetime.now(UTC)
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_out(job)


@router.get("/export/file")
def export_file(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_project(project_id, user, db)
    job = db.query(EditingJob).filter(EditingJob.project_id == project_id,
                                      EditingJob.job_type.in_(["export", "remove", "replace", "restyle"]),
                                      EditingJob.status == "done").order_by(EditingJob.completed_at.desc()).first()
    key = (job.job_metadata or {}).get("result", "") if job else ""
    if not key:
        raise HTTPException(status_code=404, detail="no exported video yet")
    path = get_storage().local_path(key)
    if not path.exists():
        raise HTTPException(status_code=404, detail="export file missing")
    return FileResponse(path, media_type="video/mp4", filename=f"reframe_{project_id[:8]}.mp4")


@router.get("/results")
def results(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_project(project_id, user, db)
    assets = db.query(VideoAsset).filter(VideoAsset.project_id == project_id,
                                        VideoAsset.asset_type == "result").order_by(VideoAsset.created_at.desc()).all()
    return [{"id": a.id, "path": a.storage_path, "metadata": a.asset_metadata or {}} for a in assets]
