"""Mask helpers: RLE-free PNG storage, overlay rendering, morphology."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


def save_mask(mask: np.ndarray, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    m = (mask > 0).astype(np.uint8) * 255
    cv2.imwrite(str(dest), m)
    return dest


def load_mask(path: Path, shape: tuple[int, int] | None = None) -> np.ndarray:
    m = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if m is None:
        raise FileNotFoundError(f"mask not found: {path}")
    if shape is not None and (m.shape[0], m.shape[1]) != shape:
        m = cv2.resize(m, (shape[1], shape[0]), interpolation=cv2.INTER_NEAREST)
    return (m > 127).astype(np.uint8)


def bounding_box(mask: np.ndarray) -> dict[str, int]:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        h, w = mask.shape[:2]
        return {"x1": 0, "y1": 0, "x2": w, "y2": h, "w": w, "h": h}
    h, w = mask.shape[:2]
    return {
        "x1": int(xs.min()), "y1": int(ys.min()),
        "x2": int(xs.max()), "y2": int(ys.max()),
        "w": int(w), "h": int(h),
    }


def refine_mask(mask: np.ndarray, kernel: int = 5, dilate: int = 0) -> np.ndarray:
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel, kernel))
    out = cv2.morphologyEx((mask * 255).astype(np.uint8), cv2.MORPH_CLOSE, k)
    if dilate:
        kd = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate * 2 + 1, dilate * 2 + 1))
        out = cv2.dilate(out, kd)
    return (out > 127).astype(np.uint8)


def overlay_mask(frame_bgr: np.ndarray, mask: np.ndarray, color=(64, 128, 255), alpha: float = 0.45) -> np.ndarray:
    m = (mask > 0).astype(np.uint8)
    colored = np.zeros_like(frame_bgr)
    colored[:] = color
    blended = frame_bgr.astype(np.float32) * (1 - alpha * m[..., None]) + colored.astype(np.float32) * (alpha * m[..., None])
    out = blended.astype(np.uint8)
    contours, _ = cv2.findContours(m * 255, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cv2.drawContours(out, contours, -1, (255, 255, 255), 1)
    return out


def ellipse_mask_from_box(h: int, w: int, box: dict) -> np.ndarray:
    """Fallback mask when a decoded raster is unavailable: ellipse inscribed in box."""
    m = np.zeros((h, w), dtype=np.uint8)
    x1, y1 = max(0, int(box.get("x1", 0))), max(0, int(box.get("y1", 0)))
    x2, y2 = min(w, int(box.get("x2", w))), min(h, int(box.get("y2", h)))
    if x2 > x1 and y2 > y1:
        cv2.ellipse(m, ((x1 + x2) // 2, (y1 + y2) // 2),
                    ((x2 - x1) // 2, (y2 - y1) // 2), 0, 0, 360, 1, -1)
    return m
