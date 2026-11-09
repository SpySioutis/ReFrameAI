"""Temporal processing: optical-flow mask propagation + flicker reduction."""

from __future__ import annotations

import cv2
import numpy as np


def propagate_mask(prev_frame_bgr: np.ndarray, next_frame_bgr: np.ndarray, prev_mask: np.ndarray) -> np.ndarray:
    """Warp prev_mask into next frame using Farneback optical flow."""
    prev_gray = cv2.cvtColor(prev_frame_bgr, cv2.COLOR_BGR2GRAY)
    next_gray = cv2.cvtColor(next_frame_bgr, cv2.COLOR_BGR2GRAY)
    flow = cv2.calcOpticalFlowFarneback(prev_gray, next_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)  # type: ignore[call-overload]
    h, w = prev_mask.shape[:2]
    grid_x, grid_y = np.meshgrid(np.arange(w), np.arange(h))
    map_x = (grid_x + flow[..., 0]).astype(np.float32)
    map_y = (grid_y + flow[..., 1]).astype(np.float32)
    warped = cv2.remap((prev_mask * 255).astype(np.uint8), map_x, map_y,
                       interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    return (warped > 127).astype(np.uint8)


def temporal_smooth_1d(values: list[float], window: int = 5) -> list[float]:
    if window <= 1 or not values:
        return values
    half = window // 2
    out = []
    for i in range(len(values)):
        lo, hi = max(0, i - half), min(len(values), i + half + 1)
        out.append(sum(values[lo:hi]) / (hi - lo))
    return out
