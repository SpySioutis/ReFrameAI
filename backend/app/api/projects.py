from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Project, User
from ..schemas import ProjectCreate, ProjectOut
from .deps import current_user, owned_project

router = APIRouter(prefix="/api/projects", tags=["projects"])


def _out(p: Project) -> ProjectOut:
    return ProjectOut(
        id=p.id, name=p.name, source_video=p.source_video, thumbnail=p.thumbnail,
        duration=p.duration, fps=p.fps, resolution=p.resolution, status=p.status,
        created_at=p.created_at.isoformat() if p.created_at else "",
        updated_at=p.updated_at.isoformat() if p.updated_at else "",
    )


@router.get("", response_model=list[ProjectOut])
def list_projects(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(Project).filter(Project.user_id == user.id).order_by(Project.updated_at.desc()).all()
    return [_out(p) for p in rows]


@router.post("", response_model=ProjectOut)
def create_project(body: ProjectCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = Project(user_id=user.id, name=body.name or "Untitled project")
    db.add(p)
    db.commit()
    db.refresh(p)
    return _out(p)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _out(owned_project(project_id, user, db))


@router.delete("/{project_id}")
def delete_project(project_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = owned_project(project_id, user, db)
    db.delete(p)
    db.commit()
    return {"ok": True}
