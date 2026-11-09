"""Removal (inpainting) + replacement (compositing) pipelines.

Removal uses OpenCV inpainting per frame with optical-flow-propagated masks and
light temporal smoothing — a maintained, dependency-free baseline that runs
locally. The module is structured as a provider so ProPainter or another
video-inpainting engine can replace `inpaint_frame` without touching the API.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .masks import load_mask, refine_mask
from .temporal import propagate_mask


def inpaint_frame(frame_bgr: np.ndarray, mask: np.ndarray, radius: float = 4.0) -> np.ndarray:
    m = refine_mask(mask, kernel=5, dilate=2)
    if m.sum() == 0:
        return frame_bgr
    return cv2.inpaint(frame_bgr, (m * 255).astype(np.uint8), float(radius), cv2.INPAINT_TELEA)


def composite_replacement(
    frame_bgr: np.ndarray,
    mask: np.ndarray,
    replacement_bgr: np.ndarray,
    feather: int = 3,
) -> np.ndarray:
    """Alpha-blend a replacement image (same size as frame) inside the mask."""
    h, w = frame_bgr.shape[:2]
    if replacement_bgr.shape[:2] != (h, w):
        replacement_bgr = cv2.resize(replacement_bgr, (w, h))
    m = (mask * 255).astype(np.uint8)
    if feather > 0:
        m = cv2.GaussianBlur(m, (feather * 2 + 1, feather * 2 + 1), 0)  # type: ignore[assignment]
    alpha = (m.astype(np.float32) / 255.0)[..., None]
    return (frame_bgr * (1 - alpha) + replacement_bgr * alpha).astype(np.uint8)


def process_video_removal(
    src: Path,
    masks: dict[int, Path],
    work_frames: Path,
    frame_shape: tuple[int, int],
    progress_cb=None,  # type: ignore[no-untyped-def]
) -> int:
    """Read src frame-by-frame, inpaint masked frames, write PNGs. Returns frame count."""
    work_frames.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(src))
    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        idx = 0
        prev_frame: np.ndarray | None = None
        prev_mask: np.ndarray | None = None
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            mask: np.ndarray | None = None
            if idx in masks:
                mask = load_mask(masks[idx], frame_shape)
                prev_mask = mask
            elif prev_mask is not None and prev_frame is not None:
                # Propagate the last known mask forward so tracking gaps
                # still get consistent removal instead of flicker.
                try:
                    mask = propagate_mask(prev_frame, frame, prev_mask)
                    prev_mask = mask
                except Exception:
                    mask = None
            out = inpaint_frame(frame, mask) if mask is not None and mask.sum() > 0 else frame
            cv2.imwrite(str(work_frames / f"frame_{idx:06d}.png"), out)
            prev_frame = frame
            idx += 1
            if progress_cb and total:
                progress_cb(idx / total)
        return idx
    finally:
        cap.release()
