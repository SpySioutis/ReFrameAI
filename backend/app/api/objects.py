from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..ai.sam import SAMError
from ..core.storage import get_storage
from ..db import get_db
from ..models import DetectedObject, EditingJob, SegmentationMask, User
from ..schemas import (
    DetectedObjectOut,
    JobOut,
    RefineRequest,
    SegmentRequest,
    SegmentResponse,
    TrackRequest,
)
from ..services import job_service, segment_service
from .deps import current_user, owned_project

router = APIRouter(prefix="/api/projects/{project_id}/objects", tags=["objects"])


@router.post("/segment", response_model=SegmentResponse)
def segment(project_id: str, body: SegmentRequest,
            user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    if not project.source_video:
        raise HTTPException(status_code=400, detail="upload a video first")
    if not body.points and body.box is None and not body.concept.strip():
        raise HTTPException(status_code=400, detail="provide points, a box, or a concept")
    try:
        res = segment_service.segment_frame(
            project_id, project.source_video, body.frame_number,
            points=[(p.x, p.y, p.label) for p in body.points],
            box=(body.box.x1, body.box.y1, body.box.x2, body.box.y2) if body.box else None,
            concept=body.concept.strip(),
        )
    except SAMError as e:
        raise HTTPException(status_code=e.status, detail=str(e))
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    return SegmentResponse(object_id=res["object_id"], tracking_id=res["tracking_id"],
                           frame_number=body.frame_number, box=res["box"], mask_id=res["mask_id"],
                           confidence=res["confidence"], provider=res["provider"])


@router.post("/track", response_model=JobOut)
def track(project_id: str, body: TrackRequest,
          user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    if not project.source_video:
        raise HTTPException(status_code=400, detail="upload a video first")
    obj = db.get(DetectedObject, body.object_id)
    if not obj or obj.project_id != project_id:
        raise HTTPException(status_code=404, detail="object not found")
    job = EditingJob(project_id=project_id, job_type="track", status="queued",
                     job_metadata={"object_id": body.object_id})
    db.add(job)
    db.commit()
    db.refresh(job)
    src, s, e, d = project.source_video, body.start_frame, body.end_frame, body.direction
    job_service.submit(job.id, lambda: segment_service.run_track(job.id, project_id, body.object_id, src, s, e, d))
    return JobOut(id=job.id, job_type=job.job_type, status=job.status, progress=job.progress,
                  metadata=job.job_metadata or {})


@router.post("/refine", response_model=SegmentResponse)
def refine(project_id: str, body: RefineRequest,
           user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    obj = db.get(DetectedObject, body.object_id)
    if not obj or obj.project_id != project_id:
        raise HTTPException(status_code=404, detail="object not found")
    try:
        res = segment_service.segment_frame(
            project_id, project.source_video, body.frame_number,
            points=[(p.x, p.y, p.label) for p in body.points],
            box=(body.box.x1, body.box.y1, body.box.x2, body.box.y2) if body.box else None,
            object_name=obj.object_name,
        )
    except (ValueError, RuntimeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    # Re-point the new mask row to the existing object and drop the temp object.
    new_obj = db.get(DetectedObject, res["object_id"])
    if new_obj:
        for m in list(new_obj.masks):
            m.object_id = obj.id
        db.delete(new_obj)
        db.commit()
    return SegmentResponse(object_id=obj.id, tracking_id=obj.tracking_id,
                           frame_number=body.frame_number, box=res["box"], mask_id=res["mask_id"],
                           confidence=res["confidence"], provider=res["provider"])


@router.get("", response_model=list[DetectedObjectOut])
def list_objects(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_project(project_id, user, db)
    rows = db.query(DetectedObject).filter(DetectedObject.project_id == project_id).all()
    return [DetectedObjectOut(id=o.id, name=o.object_name, tracking_id=o.tracking_id,
                              mask_count=len(o.masks)) for o in rows]


@router.get("/{object_id}/masks/{frame_number}")
def mask_image(project_id: str, object_id: str, frame_number: int,
               user: User = Depends(current_user), db: Session = Depends(get_db)):
    owned_project(project_id, user, db)
    row = db.query(SegmentationMask).filter(
        SegmentationMask.object_id == object_id,
        SegmentationMask.frame_number == frame_number).first()
    if not row:
        raise HTTPException(status_code=404, detail="no mask for this frame")
    path = get_storage().local_path(row.mask_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="mask file missing")
    return FileResponse(path, media_type="image/png")
