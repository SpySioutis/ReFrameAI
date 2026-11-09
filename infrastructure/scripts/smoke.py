#!/usr/bin/env python3
"""End-to-end API smoke test: synthetic video -> upload -> segment -> track -> remove -> export.

Usage (backend running on :8000):
    cd backend && uv run python ../infrastructure/scripts/smoke.py [BASE_URL]
"""

from __future__ import annotations

import sys
import tempfile
import time
import uuid
from pathlib import Path

import cv2
import httpx
import numpy as np

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


def make_video(path: Path, frames: int = 60, w: int = 320, h: int = 240, fps: int = 30) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    for i in range(frames):
        img = np.full((h, w, 3), 90, dtype=np.uint8)
        x = 20 + int(i * (w - 100) / frames)
        cv2.rectangle(img, (x, 80), (x + 60, 140), (0, 0, 220), -1)
        out.write(img)
    out.release()


def poll_job(client: httpx.Client, job_id: str, timeout: int = 300) -> dict:
    start = time.time()
    while time.time() - start < timeout:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("done", "failed", "cancelled"):
            return j
        time.sleep(1.0)
    raise RuntimeError(f"job {job_id} timed out")


def main() -> None:
    client = httpx.Client(base_url=BASE, timeout=120.0)
    assert client.get("/api/health").json()["ok"], "backend not reachable"

    email = f"smoke-{uuid.uuid4().hex[:8]}@t.co"
    token = client.post("/api/auth/register", json={"email": email, "password": "password123"}).json()["token"]
    client.headers["Authorization"] = f"Bearer {token}"
    print(f"registered {email}")

    project = client.post("/api/projects", json={"name": "smoke"}).json()
    pid = project["id"]
    print(f"project {pid}")

    with tempfile.TemporaryDirectory() as tmp:
        vid = Path(tmp) / "smoke.mp4"
        make_video(vid)
        with open(vid, "rb") as f:
            r = client.post(f"/api/projects/{pid}/video", files={"file": ("smoke.mp4", f, "video/mp4")}, timeout=180.0)
        assert r.status_code == 200, r.text
        print("uploaded:", r.json()["resolution"], r.json()["fps"], "fps")

    meta = client.get(f"/api/projects/{pid}/video/metadata").json()
    assert meta["frames"] > 0 and meta["width"] == 320, meta
    print("metadata:", meta)

    seg = client.post(f"/api/projects/{pid}/objects/segment", json={
        "frame_number": 5, "points": [{"x": 50, "y": 110, "label": "positive"}]}).json()
    assert seg["object_id"], seg
    print(f"segmented: provider={seg['provider']} box={seg['box']}")
    oid = seg["object_id"]

    track = client.post(f"/api/projects/{pid}/objects/track", json={
        "object_id": oid, "start_frame": 5, "end_frame": 20}).json()
    tj = poll_job(client, track["id"])
    assert tj["status"] == "done", tj
    print("tracked:", tj["metadata"])

    rm = client.post(f"/api/projects/{pid}/edit/remove", json={"object_id": oid, "prompt": "remove"}).json()
    rj = poll_job(client, rm["id"])
    assert rj["status"] == "done", rj.get("error_message", rj)[:500]
    print("removed:", rj["metadata"].get("result"))

    exp = client.post(f"/api/projects/{pid}/export", json={}).json()
    assert exp["status"] == "done", exp
    content = client.get(f"/api/projects/{pid}/export/file").content
    assert len(content) > 1_000, f"export too small: {len(content)}"
    print(f"exported MP4: {len(content)} bytes")

    chat = client.post("/api/assistant/chat", json={
        "project_id": pid, "messages": [{"role": "user", "content": "Remove the red square"}]}).json()
    assert chat["plan"]["operation"] == "remove", chat
    print("assistant:", chat["reply"][:100])

    print("\nSMOKE OK — upload → segment → track → remove → export → assistant")


if __name__ == "__main__":
    main()
