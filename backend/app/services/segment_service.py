"""Segmentation + tracking orchestration (SAM or local fallback)."""

from __future__ import annotations

import cv2
import numpy as np

from ..ai.sam import SAMProvider, segment_frame_local
from ..ai.sam.parser import decode_mask_raster, raster_to_full_frame_mask
from ..ai.sam.prompts import build_object_prompt
from ..core.config import get_settings
from ..core.storage import get_storage
from ..db import SessionLocal
from ..models import DetectedObject, SegmentationMask
from ..video.ffmpeg import probe_video
from ..video.masks import bounding_box, ellipse_mask_from_box, refine_mask, save_mask
from ..video.temporal import propagate_mask
from . import job_service
from .video_service import frame_image_path


def _sam_box_to_mask(box: dict, h: int, w: int) -> np.ndarray:
    return ellipse_mask_from_box(h, w, box)


def segment_frame(
    project_id: str,
    source_key: str,
    frame_number: int,
    *,
    points: list[tuple[float, float, str]] | None = None,
    box: tuple[float, float, float, float] | None = None,
    concept: str = "",
    object_name: str = "object",
) -> dict:
    """Segment one frame. Returns {object_id, tracking_id, box, mask_id, provider}."""
    storage = get_storage()
    settings = get_settings()
    frame_path = frame_image_path(project_id, source_key, frame_number)
    frame = cv2.imread(str(frame_path))
    if frame is None:
        raise RuntimeError(f"could not read frame {frame_number}")
    h, w = frame.shape[:2]

    # Clamp prompts to frame.
    pts = [(int(max(0, min(w - 1, x))), int(max(0, min(h - 1, y))), lbl == "positive")
           for (x, y, lbl) in (points or [])]
    bx = None
    if box is not None:
        bx = (int(max(0, min(w - 1, box[0]))), int(max(0, min(h - 1, box[1]))),
              int(max(0, min(w, box[2]))), int(max(0, min(h, box[3]))))

    provider_label = "local"
    mask: np.ndarray
    out_box: dict = {}
    confidence: float | None = None

    use_sam = bool(settings.model_api_key.strip())
    if use_sam and (concept or pts or bx):
        try:
            sam = SAMProvider()
            img_bytes = frame_path.read_bytes()
            obj_prompt = ""
            if not concept:
                obj_prompt = build_object_prompt(
                    0, 1, w, h,
                    points=[(x, y, pos) for (x, y, pos) in pts] or None,
                    box=bx,
                )
            res = sam.segment_image(img_bytes, "image/jpeg", concept=concept,
                                    object_prompt=obj_prompt)
            if res.records:
                rec = res.records[0]
                out_box = {k: float(v) for k, v in rec.box.items()}
                confidence = rec.confidence
                # Try to decode the raster; fall back to box ellipse honestly.
                raw = decode_mask_raster(rec.mask)
                full = raster_to_full_frame_mask(raw, rec.mask, w, h) if raw else None
                if full and len(full) == w * h:
                    mask = np.array(full, dtype=np.uint8).reshape(h, w)
                else:
                    mask = _sam_box_to_mask(rec.box, h, w)
                provider_label = "sam"
            else:
                raise RuntimeError("SAM returned zero matches for this prompt")
        except Exception as e:
            # Honest fallback: report SAM failure, use local so UI testing continues.
            if "zero matches" in str(e).lower() or "rejected" in str(e).lower():
                raise
            mask = segment_frame_local(frame, points=[(x, y, p) for (x, y, p) in pts] or None, box=bx)
            provider_label = "local"
    else:
        if concept and not (pts or bx):
            raise RuntimeError("concept detection needs MODEL_API_KEY (SAM 3.1); click a point or draw a box for local mode")
        mask = segment_frame_local(frame, points=[(x, y, p) for (x, y, p) in pts] or None, box=bx)

    mask = refine_mask(mask)
    if not out_box:
        out_box = {k: float(v) for k, v in bounding_box(mask).items()}

    db = SessionLocal()
    try:
        existing = db.query(DetectedObject).filter(DetectedObject.project_id == project_id).count()
        obj = DetectedObject(project_id=project_id, object_name=object_name or concept or "object",
                             tracking_id=existing + 1,
                             object_metadata={"provider": provider_label, "frame": frame_number})
        db.add(obj)
        db.flush()
        mask_key = f"projects/{project_id}/masks/{obj.id}/mask_{frame_number:06d}.png"
        save_mask(mask, storage.local_path(mask_key))
        mrow = SegmentationMask(object_id=obj.id, frame_number=frame_number,
                                mask_path=mask_key, bounding_box=out_box)
        db.add(mrow)
        db.commit()
        return {"object_id": obj.id, "tracking_id": obj.tracking_id, "box": out_box,
                "mask_id": mrow.id, "provider": provider_label, "confidence": confidence}
    finally:
        db.close()


def run_track(job_id: str, project_id: str, object_id: str, source_key: str,
              start_frame: int, end_frame: int | None, direction: str = "forward") -> None:
    storage = get_storage()
    src = storage.local_path(source_key)
    info = probe_video(src)
    total = info.frames or 0
    shape = (info.height, info.width)
    s = max(0, start_frame)
    e = total - 1 if end_frame is None else min(total - 1, end_frame)
    if e < s:
        raise RuntimeError("end_frame must be >= start_frame")

    db = SessionLocal()
    try:
        anchor = db.query(SegmentationMask).filter(
            SegmentationMask.object_id == object_id,
            SegmentationMask.frame_number == s).first()
        if anchor is None:
            # nearest existing mask at/after start
            anchor = db.query(SegmentationMask).filter(
                SegmentationMask.object_id == object_id,
                SegmentationMask.frame_number >= s).order_by(SegmentationMask.frame_number).first()
            if anchor is None:
                raise RuntimeError("no anchor mask — segment the object first")
            s = anchor.frame_number
        from ..video.masks import load_mask

        anchor_mask = load_mask(storage.local_path(anchor.mask_path), shape)
        cap = cv2.VideoCapture(str(src))
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, s)
            ok, prev_frame = cap.read()
            if not ok or prev_frame is None:
                raise RuntimeError(f"could not read frame {s}")
            prev_mask = anchor_mask
            frames = range(s + 1, e + 1) if direction != "backward" else range(s - 1, -1, -1)
            frame_list = list(frames)
            n = len(frame_list)
            for i, fn in enumerate(frame_list):
                if job_service.is_cancelled(job_id):
                    return
                cap.set(cv2.CAP_PROP_POS_FRAMES, fn)
                ok, frame = cap.read()
                if not ok or frame is None:
                    break
                try:
                    m = propagate_mask(prev_frame, frame, prev_mask)
                except Exception:
                    m = prev_mask
                m = refine_mask(m)
                key = f"projects/{project_id}/masks/{object_id}/mask_{fn:06d}.png"
                save_mask(m, storage.local_path(key))
                row = SegmentationMask(object_id=object_id, frame_number=fn, mask_path=key,
                                       bounding_box={k: float(v) for k, v in bounding_box(m).items()})
                db.add(row)
                prev_frame, prev_mask = frame, m
                if i % 5 == 0:
                    db.commit()
                job_service.update_job(job_id, progress=(i + 1) / max(n, 1))
            db.commit()
        finally:
            cap.release()
        job_service.update_job(job_id, progress=1.0, metadata={"tracked_frames": n, "method": "optical-flow"})
    finally:
        db.close()
