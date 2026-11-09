"""Local (offline) segmentation fallback using classic computer vision.

Used ONLY when Meta API credentials are unavailable, so the editor UI,
coordinate mapping, mask overlay, tracking and export pipelines can still be
exercised end-to-end. Results are clearly labeled provider="local".
"""

from __future__ import annotations

import cv2
import numpy as np


def segment_click(frame_bgr: np.ndarray, x: int, y: int, radius: int = 24) -> np.ndarray:
    """GrabCut seeded by a small box around the click + flood-fill assist."""
    h, w = frame_bgr.shape[:2]
    x = max(0, min(w - 1, x))
    y = max(0, min(h - 1, y))
    x1, y1 = max(0, x - radius * 3), max(0, y - radius * 3)
    x2, y2 = min(w, x + radius * 3), min(h, y + radius * 3)
    mask = np.zeros((h, w), dtype=np.uint8)
    if x2 - x1 < 5 or y2 - y1 < 5:
        cv2.circle(mask, (x, y), radius, 1, -1)
        return mask
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(frame_bgr, mask, (x1, y1, x2 - x1, y2 - y1), bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
        out = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
        if out.sum() < 25:
            raise RuntimeError("empty grabcut")
        # Keep only the connected component containing the click.
        n, labels, _stats, _ = cv2.connectedComponentsWithStats(out, 8)  # type: ignore[call-overload]
        if n > 1:
            keep = labels[y, x]
            if keep > 0:
                out = (labels == keep).astype(np.uint8)
        return out
    except Exception:
        # Flood-fill fallback on a blurred grayscale image.
        gray = cv2.GaussianBlur(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY), (5, 5), 0)
        ff = np.zeros((h + 2, w + 2), dtype=np.uint8)
        flood = gray.copy()
        cv2.floodFill(flood, ff, (x, y), 255, loDiff=12, upDiff=12)
        out = ((flood > 200).astype(np.uint8))
        if out.sum() < 25 or out.sum() > 0.9 * w * h:
            out = np.zeros((h, w), dtype=np.uint8)
            cv2.circle(out, (x, y), radius, 1, -1)
        return out


def segment_box(frame_bgr: np.ndarray, x1: int, y1: int, x2: int, y2: int) -> np.ndarray:
    h, w = frame_bgr.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    mask = np.zeros((h, w), dtype=np.uint8)
    if x2 - x1 < 5 or y2 - y1 < 5:
        return mask
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(frame_bgr, mask, (x1, y1, x2 - x1, y2 - y1), bgd, fgd, 3, cv2.GC_INIT_WITH_RECT)
        return np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 1, 0).astype(np.uint8)
    except Exception:
        cv2.rectangle(mask, (x1, y1), (x2, y2), 1, -1)
        return mask
