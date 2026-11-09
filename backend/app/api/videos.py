from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..core.storage import get_storage
from ..db import get_db
from ..models import User, VideoAsset
from ..schemas import ProjectOut, VideoMetadata
from ..services import video_service
from ..video.ffmpeg import probe_video
from .deps import current_user, owned_project

router = APIRouter(prefix="/api", tags=["video"])


@router.post("/projects/{project_id}/video", response_model=ProjectOut)
async def upload_video(project_id: str, file: UploadFile,
                       user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    try:
        key, _ = await video_service.save_upload(project_id, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    info = probe_video(get_storage().local_path(key))
    project.source_video = key
    project.duration = info.duration
    project.fps = info.fps
    project.resolution = f"{info.width}x{info.height}" if info.width else ""
    project.status = "ready"
    try:
        project.thumbnail = video_service.ensure_thumbnail(project_id, key)
    except Exception:
        project.thumbnail = ""
    db.add(VideoAsset(project_id=project_id, asset_type="source", storage_path=key,
                       asset_metadata={"duration": info.duration, "fps": info.fps}))
    db.commit()
    db.refresh(project)
    return ProjectOut(id=project.id, name=project.name, source_video=project.source_video,
                      thumbnail=project.thumbnail, duration=project.duration, fps=project.fps,
                      resolution=project.resolution, status=project.status,
                      created_at=project.created_at.isoformat() if project.created_at else "",
                      updated_at=project.updated_at.isoformat() if project.updated_at else "")


@router.get("/projects/{project_id}/video/metadata", response_model=VideoMetadata)
def video_metadata(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    if not project.source_video:
        raise HTTPException(status_code=404, detail="no video uploaded")
    info = probe_video(get_storage().local_path(project.source_video))
    return VideoMetadata(duration=info.duration, fps=info.fps, width=info.width,
                         height=info.height, frames=info.frames, has_audio=info.has_audio,
                         codec=info.codec)


@router.get("/projects/{project_id}/video/file")
def video_file(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    if not project.source_video:
        raise HTTPException(status_code=404, detail="no video uploaded")
    path = get_storage().local_path(project.source_video)
    if not path.exists():
        raise HTTPException(status_code=404, detail="video file missing")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@router.get("/projects/{project_id}/video/thumbnail")
def thumbnail(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    if not project.thumbnail:
        raise HTTPException(status_code=404, detail="no thumbnail")
    path = get_storage().local_path(project.thumbnail)
    if not path.exists():
        raise HTTPException(status_code=404, detail="thumbnail missing")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/projects/{project_id}/frames/{frame_number}")
def frame_image(project_id: str, frame_number: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    project = owned_project(project_id, user, db)
    if not project.source_video:
        raise HTTPException(status_code=404, detail="no video uploaded")
    try:
        path = video_service.frame_image_path(project_id, project.source_video, frame_number)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return FileResponse(path, media_type="image/jpeg")
