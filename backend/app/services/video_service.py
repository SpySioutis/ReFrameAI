"""Video upload + metadata + frame helpers."""

from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from ..core.config import get_settings
from ..core.storage import get_storage
from ..video.ffmpeg import VideoInfo, extract_frame, make_thumbnail, probe_video

ALLOWED_EXT = {".mp4", ".mov", ".webm"}
ALLOWED_MIME = {"video/mp4", "video/quicktime", "video/webm"}


def validate_upload(filename: str, content_type: str, size: int) -> None:
    settings = get_settings()
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(f"unsupported format '{ext}' — use MP4, MOV or WebM")
    if content_type and content_type not in ALLOWED_MIME and not content_type.startswith("video/"):
        raise ValueError(f"unsupported media type '{content_type}'")
    if size > settings.max_upload_mb * 1024 * 1024:
        raise ValueError(f"file exceeds {settings.max_upload_mb} MB limit")


async def save_upload(project_id: str, upload: UploadFile) -> tuple[str, int]:
    storage = get_storage()
    ext = Path(upload.filename or "video.mp4").suffix.lower() or ".mp4"
    key = f"projects/{project_id}/source{ext}"
    # Stream to disk without loading whole file into RAM.
    local_path = storage.local_path(key)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with open(local_path, "wb") as f:  # noqa: ASYNC230 - chunked upload write, acceptable in MVP
        while chunk := await upload.read(1024 * 1024):
            f.write(chunk)
            size += len(chunk)
    validate_upload(upload.filename or "", upload.content_type or "", size)
    info = probe_video(local_path)
    settings = get_settings()
    if info.duration > settings.max_duration_sec:
        local_path.unlink(missing_ok=True)
        raise ValueError(f"video exceeds {settings.max_duration_sec}s duration limit")
    return key, size


def project_video_info(project_source_key: str) -> VideoInfo:
    storage = get_storage()
    return probe_video(storage.local_path(project_source_key))


def ensure_thumbnail(project_id: str, source_key: str) -> str:
    storage = get_storage()
    key = f"projects/{project_id}/thumbnail.jpg"
    if storage.exists(key):
        return key
    make_thumbnail(storage.local_path(source_key), storage.local_path(key))
    return key


def frame_image_path(project_id: str, source_key: str, frame_number: int) -> Path:
    storage = get_storage()
    dest = storage.local_path(f"projects/{project_id}/frames/frame_{frame_number:06d}.jpg")
    if not dest.exists():
        extract_frame(storage.local_path(source_key), frame_number, dest)
    return dest
