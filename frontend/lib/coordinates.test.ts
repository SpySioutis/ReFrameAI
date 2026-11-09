import { describe, expect, it } from "vitest";
import { clampBox, contentRect, screenToVideo, videoToScreen } from "./coordinates";

describe("contentRect", () => {
  it("centers a 16:9 video in a square container (letterbox)", () => {
    const r = contentRect(600, 600, 1920, 1080);
    expect(r.w).toBeCloseTo(600);
    expect(r.h).toBeCloseTo(337.5);
    expect(r.x).toBeCloseTo(0);
    expect(r.y).toBeCloseTo((600 - 337.5) / 2);
  });

  it("fills exactly when aspect ratios match", () => {
    const r = contentRect(640, 360, 1920, 1080);
    expect(r).toEqual({ x: 0, y: 0, w: 640, h: 360 });
  });
});

describe("screenToVideo", () => {
  it("maps the documented SAM example: (100,50) on 640x360 preview of 1920x1080", () => {
    const p = screenToVideo(100, 50, 640, 360, 1920, 1080);
    expect(p).toEqual({ x: 300, y: 150 });
  });

  it("accounts for letterboxing", () => {
    // 600x600 container, 1920x1080 video -> picture is 600x337.5 at y=131.25
    const p = screenToVideo(300, 300, 600, 600, 1920, 1080);
    expect(p).toEqual({ x: 960, y: 540 });
  });

  it("returns null for clicks on the letterbox bars", () => {
    expect(screenToVideo(300, 10, 600, 600, 1920, 1080)).toBeNull();
  });
});

describe("videoToScreen round-trip", () => {
  it("round-trips within a pixel", () => {
    const v = { x: 1234, y: 567 };
    const s = videoToScreen(v.x, v.y, 800, 600, 1920, 1080);
    const back = screenToVideo(s.x, s.y, 800, 600, 1920, 1080);
    expect(back).not.toBeNull();
    expect(Math.abs(back!.x - v.x)).toBeLessThanOrEqual(1);
    expect(Math.abs(back!.y - v.y)).toBeLessThanOrEqual(1);
  });
});

describe("clampBox", () => {
  it("clamps and normalizes", () => {
    expect(clampBox(2000, -10, 100, 5000, 1920, 1080)).toEqual({
      x1: 100,
      y1: 0,
      x2: 1920,
      y2: 1080,
    });
  });
});
