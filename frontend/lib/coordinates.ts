/**
 * Screen <-> source-video coordinate mapping.
 *
 * The <video> element uses object-fit: contain inside a fixed-size container,
 * so the picture may be letterboxed. Clicks must be converted to source
 * pixels before being sent to SAM (docs: "Scale coordinates before you send
 * them"). All math is pure and unit-tested.
 */

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

/** Where the video picture sits inside its container (letterbox-aware). */
export function contentRect(
  containerW: number,
  containerH: number,
  videoW: number,
  videoH: number
): Rect {
  if (containerW <= 0 || containerH <= 0 || videoW <= 0 || videoH <= 0) {
    return { x: 0, y: 0, w: 0, h: 0 };
  }
  const scale = Math.min(containerW / videoW, containerH / videoH);
  const w = videoW * scale;
  const h = videoH * scale;
  return { x: (containerW - w) / 2, y: (containerH - h) / 2, w, h };
}

/** Click (container-relative px) -> source video px. Returns null if outside picture. */
export function screenToVideo(
  clickX: number,
  clickY: number,
  containerW: number,
  containerH: number,
  videoW: number,
  videoH: number
): { x: number; y: number } | null {
  const r = contentRect(containerW, containerH, videoW, videoH);
  if (r.w <= 0 || r.h <= 0) return null;
  const px = clickX - r.x;
  const py = clickY - r.y;
  if (px < 0 || py < 0 || px > r.w || py > r.h) return null;
  return {
    x: Math.floor((px / r.w) * videoW),
    y: Math.floor((py / r.h) * videoH),
  };
}

/** Source video px -> container-relative px (for drawing overlays). */
export function videoToScreen(
  vx: number,
  vy: number,
  containerW: number,
  containerH: number,
  videoW: number,
  videoH: number
): { x: number; y: number } {
  const r = contentRect(containerW, containerH, videoW, videoH);
  return {
    x: r.x + (vx / videoW) * r.w,
    y: r.y + (vy / videoH) * r.h,
  };
}

/** Clamp a box to the source frame. */
export function clampBox(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  videoW: number,
  videoH: number
): { x1: number; y1: number; x2: number; y2: number } {
  const cx = (v: number, m: number) => Math.max(0, Math.min(m, Math.floor(v)));
  return {
    x1: cx(Math.min(x1, x2), videoW),
    y1: cx(Math.min(y1, y2), videoH),
    x2: cx(Math.max(x1, x2), videoW),
    y2: cx(Math.max(y1, y2), videoH),
  };
}
