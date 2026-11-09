"""Database models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


def _uid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    projects: Mapped[list[Project]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    user_id: Mapped[str] = mapped_column(String(32), ForeignKey("users.id"), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="Untitled project")
    source_video: Mapped[str] = mapped_column(String(1024), default="")
    thumbnail: Mapped[str] = mapped_column(String(1024), default="")
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    resolution: Mapped[str] = mapped_column(String(32), default="")
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="projects")
    assets: Mapped[list[VideoAsset]] = relationship(back_populates="project", cascade="all, delete-orphan")
    objects: Mapped[list[DetectedObject]] = relationship(back_populates="project", cascade="all, delete-orphan")
    jobs: Mapped[list[EditingJob]] = relationship(back_populates="project", cascade="all, delete-orphan")
    operations: Mapped[list[EditingOperation]] = relationship(back_populates="project", cascade="all, delete-orphan")


class VideoAsset(Base):
    __tablename__ = "video_assets"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(String(32), ForeignKey("projects.id"), index=True, nullable=False)
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False)  # source|preview|result|thumbnail|frame
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    asset_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped[Project] = relationship(back_populates="assets")


class DetectedObject(Base):
    __tablename__ = "detected_objects"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(String(32), ForeignKey("projects.id"), index=True, nullable=False)
    object_name: Mapped[str] = mapped_column(String(255), default="object")
    tracking_id: Mapped[int] = mapped_column(Integer, default=0)
    object_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped[Project] = relationship(back_populates="objects")
    masks: Mapped[list[SegmentationMask]] = relationship(back_populates="obj", cascade="all, delete-orphan")


class SegmentationMask(Base):
    __tablename__ = "segmentation_masks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    object_id: Mapped[str] = mapped_column(String(32), ForeignKey("detected_objects.id"), index=True, nullable=False)
    frame_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    mask_path: Mapped[str] = mapped_column(String(1024), default="")
    bounding_box: Mapped[dict] = mapped_column(JSON, default=dict)  # {x1,y1,x2,y2,w,h}
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    obj: Mapped[DetectedObject] = relationship(back_populates="masks")


class EditingJob(Base):
    __tablename__ = "editing_jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(String(32), ForeignKey("projects.id"), index=True, nullable=False)
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)  # segment|track|remove|replace|restyle|export
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)  # queued|running|done|failed|cancelled
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    error_message: Mapped[str] = mapped_column(Text, default="")
    job_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[Project] = relationship(back_populates="jobs")


class EditingOperation(Base):
    __tablename__ = "editing_operations"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_uid)
    project_id: Mapped[str] = mapped_column(String(32), ForeignKey("projects.id"), index=True, nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("detected_objects.id"), nullable=True)
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False)  # remove|replace|restyle
    prompt: Mapped[str] = mapped_column(Text, default="")
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    result_asset: Mapped[str] = mapped_column(String(1024), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    project: Mapped[Project] = relationship(back_populates="operations")
