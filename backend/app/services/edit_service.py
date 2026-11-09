"""Editing pipelines: remove (inpaint) / replace+restyle (Muse Image + composite).

Temporal consistency strategy (documented in docs/AI_PIPELINE.md):
1. Masks exist per frame (SAM tracking or optical-flow propagation).
2. Removal: per-frame OpenCV inpainting over flow-propagated masks.
3. Replace/restyle: ONE hero image is generated with Muse Image from the
   middle keyframe crop, then warped/composited into every masked frame with
   feathered alpha. This avoids per-frame flicker from independent generation.
"""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path

import cv2
import numpy as np

from ..ai.muse_image import MuseImageProvider
from ..core.config import get_settings
from ..core.storage import get_storage
from ..db import SessionLocal
from ..models import DetectedObject, Project, SegmentationMask, VideoAsset
from ..video.ffmpeg import frames_to_video, probe_video
from ..video.inpaint import composite_replacement, process_video_removal
from ..video.masks import bounding_box, load_mask
from ..video.temporal import propagate_mask
from . import job_service


def _masks_for_object(db, object_id: str) -> dict[int, SegmentationMask]:
    rows = db.query(SegmentationMask).filter(SegmentationMask.object_id == object_id).all()
    return {r.frame_number: r for r in rows}


def run_remove(job_id: str, project_id: str, object_id: str, preserve_audio: bool = True) -> None:
    storage = get_storage()
    db = SessionLocal()
    try:
        project = db.get(Project, project_id)
        obj = db.get(DetectedObject, object_id)
        if not project or not obj or not project.source_video:
            raise RuntimeError("project, object or source video not found")
        src = storage.local_path(project.source_video)
        info = probe_video(src)
        shape = (info.height, info.width)
        mask_rows = _masks_for_object(db, object_id)
        if not mask_rows:
            raise RuntimeError("no segmentation masks for this object — segment it first")
        masks = {fn: storage.local_path(m.mask_path) for fn, m in mask_rows.items()}

        def _progress(p: float) -> None:
            job_service.update_job(job_id, progress=0.05 + 0.8 * p)

        with tempfile.TemporaryDirectory(prefix="reframe_remove_") as tmp:
            work = Path(tmp) / "frames"
            count = process_video_removal(src, masks, work, shape, progress_cb=_progress)
            job_service.update_job(job_id, progress=0.9, metadata={"frames": count})
            dest_key = f"projects/{project_id}/results/{job_id}.mp4"
            frames_to_video(work, storage.local_path(dest_key), info.fps or 30,
                            audio_src=src if (preserve_audio and info.has_audio) else None)
        asset = VideoAsset(project_id=project_id, asset_type="result", storage_path=dest_key,
                           asset_metadata={"job_id": job_id, "operation": "remove"})
        db.add(asset)
        db.commit()
        job_service.update_job(job_id, progress=1.0, metadata={"result": dest_key})
    finally:
        db.close()


def _keyframe_crop(frame: np.ndarray, mask: np.ndarray, pad: int = 24) -> tuple[np.ndarray, tuple[int, int, int, int]]:
    box = bounding_box(mask)
    h, w = frame.shape[:2]
    x1 = max(0, box["x1"] - pad)
    y1 = max(0, box["y1"] - pad)
    x2 = min(w, box["x2"] + pad)
    y2 = min(h, box["y2"] + pad)
    return frame[y1:y2, x1:x2], (x1, y1, x2, y2)


def run_replace(
    job_id: str,
    project_id: str,
    object_id: str,
    prompt: str,
    operation: str = "replace",
    preserve_audio: bool = True,
) -> None:
    settings = get_settings()
    if not settings.model_api_key.strip():
        raise RuntimeError("MODEL_API_KEY is not configured — generative replace/restyle needs Muse Image.")
    storage = get_storage()
    provider = MuseImageProvider()
    db = SessionLocal()
    try:
        project = db.get(Project, project_id)
        obj = db.get(DetectedObject, object_id)
        if not project or not obj or not project.source_video:
            raise RuntimeError("project, object or source video not found")
        src = storage.local_path(project.source_video)
        info = probe_video(src)
        shape = (info.height, info.width)
        mask_rows = _masks_for_object(db, object_id)
        if not mask_rows:
            raise RuntimeError("no segmentation masks for this object — segment it first")

        # 1. Hero keyframe: middle masked frame -> crop -> Muse Image edit.
        mid_fn = sorted(mask_rows)[len(mask_rows) // 2]
        cap = cv2.VideoCapture(str(src))
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, mid_fn)
            ok, hero = cap.read()
        finally:
            cap.release()
        if not ok or hero is None:
            raise RuntimeError(f"could not read keyframe {mid_fn}")
        hero_mask = load_mask(storage.local_path(mask_rows[mid_fn].mask_path), shape)
        crop, (cx1, cy1, cx2, cy2) = _keyframe_crop(hero, hero_mask)
        ok, buf = cv2.imencode(".png", crop)
        if not ok:
            raise RuntimeError("could not encode keyframe crop")
        full_prompt = provider.build_replacement_prompt(prompt, operation=operation,
                                                       scene_context=f"video frame {mid_fn}, {obj.object_name}")
        job_service.update_job(job_id, progress=0.1, metadata={"stage": "generating hero image"})
        gen = provider.edit(full_prompt, [("image/png", base64.b64encode(buf.tobytes()).decode())])
        gen_arr = np.frombuffer(gen.data, dtype=np.uint8)
        gen_crop = cv2.imdecode(gen_arr, cv2.IMREAD_COLOR)
        if gen_crop is None:
            raise RuntimeError("Muse Image returned an undecodable image")
        gen_crop = cv2.resize(gen_crop, (cx2 - cx1, cy2 - cy1))
        job_service.update_job(job_id, progress=0.3, metadata={"stage": "compositing frames"})

        # 2. Composite hero crop into every frame with flow-propagated masks.
        with tempfile.TemporaryDirectory(prefix="reframe_replace_") as tmp:
            work = Path(tmp) / "frames"
            work.mkdir(parents=True, exist_ok=True)
            cap = cv2.VideoCapture(str(src))
            try:
                total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                idx = 0
                prev_frame: np.ndarray | None = None
                prev_mask: np.ndarray | None = None
                base_full = np.zeros_like(hero)
                base_full[cy1:cy2, cx1:cx2] = gen_crop
                # Anchor mask = hero mask; other frames use stored or propagated masks.
                anchor = hero_mask
                while True:
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        break
                    if idx in mask_rows:
                        m = load_mask(storage.local_path(mask_rows[idx].mask_path), shape)
                        prev_mask = m
                    elif prev_mask is not None and prev_frame is not None:
                        try:
                            m = propagate_mask(prev_frame, frame, prev_mask)
                        except Exception:
                            m = anchor
                        prev_mask = m
                    else:
                        m = anchor if idx == mid_fn else np.zeros(shape, dtype=np.uint8)
                    if m.sum() > 0:
                        # Shift hero replacement to current mask centroid for motion following.
                        ys, xs = np.nonzero(m)
                        ays, axs = np.nonzero(anchor)
                        if len(xs) and len(axs):
                            dx = int(xs.mean() - axs.mean())
                            dy = int(ys.mean() - ays.mean())
                            M = np.array([[1, 0, dx], [0, 1, dy]], dtype=np.float32)
                            shifted = cv2.warpAffine(base_full, M, (shape[1], shape[0]))  # type: ignore[call-overload]
                        else:
                            shifted = base_full
                        frame = composite_replacement(frame, m, shifted)
                    cv2.imwrite(str(work / f"frame_{idx:06d}.png"), frame)
                    prev_frame = frame
                    idx += 1
                    if total:
                        job_service.update_job(job_id, progress=0.3 + 0.55 * (idx / total))
                count = idx
            finally:
                cap.release()
            dest_key = f"projects/{project_id}/results/{job_id}.mp4"
            frames_to_video(work, storage.local_path(dest_key), info.fps or 30,
                            audio_src=src if (preserve_audio and info.has_audio) else None)
        asset = VideoAsset(project_id=project_id, asset_type="result", storage_path=dest_key,
                           asset_metadata={"job_id": job_id, "operation": operation, "prompt": prompt[:500]})
        db.add(asset)
        db.commit()
        job_service.update_job(job_id, progress=1.0, metadata={"result": dest_key, "frames": count})
    finally:
        db.close()
