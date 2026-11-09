"""FFmpeg-based probing, frame extraction, thumbnails and final export."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VideoInfo:
    duration: float
    fps: float
    width: int
    height: int
    frames: int
    has_audio: bool
    codec: str


def _run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def probe_video(path: Path) -> VideoInfo:
    """Probe with ffprobe when available, else fall back to OpenCV."""
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        try:
            p = _run([
                ffprobe, "-v", "quiet", "-print_format", "json",
                "-show_streams", "-show_format", str(path),
            ])
            data = json.loads(p.stdout or "{}")
            streams = data.get("streams", [])
            v: dict = next((s for s in streams if s.get("codec_type") == "video"), {})
            a = next((s for s in streams if s.get("codec_type") == "audio"), None)
            fps_raw = v.get("avg_frame_rate") or v.get("r_frame_rate") or "0/1"
            num, _, den = fps_raw.partition("/")
            fps = float(num) / float(den or 1) if float(den or 0) else 0.0
            duration = float(data.get("format", {}).get("duration") or v.get("duration") or 0.0)
            frames = int(v.get("nb_frames") or (duration * fps if fps else 0))
            return VideoInfo(
                duration=duration, fps=fps,
                width=int(v.get("width") or 0), height=int(v.get("height") or 0),
                frames=frames, has_audio=a is not None,
                codec=str(v.get("codec_name") or ""),
            )
        except Exception:
            pass
    # OpenCV fallback
    import cv2

    cap = cv2.VideoCapture(str(path))
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        duration = frames / fps if fps else 0.0
        return VideoInfo(duration=duration, fps=fps, width=w, height=h,
                         frames=frames, has_audio=False, codec="")
    finally:
        cap.release()


def extract_frame(src: Path, frame_number: int, dest: Path, fps: float = 0.0) -> Path:
    """Extract an exact frame by number (accurate seek via select filter)."""
    import cv2

    dest.parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(src))
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError(f"could not read frame {frame_number}")
        cv2.imwrite(str(dest), frame)
        return dest
    finally:
        cap.release()


def make_thumbnail(src: Path, dest: Path, width: int = 480) -> Path:
    import cv2

    dest.parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(src))
    try:
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 1)
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(total // 4, total - 1))
        ok, frame = cap.read()
        if not ok or frame is None:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError("could not read video for thumbnail")
        h, w = frame.shape[:2]
        scale = width / max(w, 1)
        thumb = cv2.resize(frame, (width, max(1, int(h * scale))))
        cv2.imwrite(str(dest), thumb)
        return dest
    finally:
        cap.release()


def frames_to_video(
    frames_dir: Path,
    dest: Path,
    fps: float,
    audio_src: Path | None = None,
    pattern: str = "frame_%06d.png",
) -> Path:
    """Re-encode PNG frames to H.264 MP4 (+faststart), optionally muxing source audio."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required for video export but was not found on PATH")
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y",
        "-framerate", f"{fps or 30:.3f}",
        "-i", str(frames_dir / pattern),
    ]
    if audio_src is not None:
        cmd += ["-i", str(audio_src), "-c:a", "aac", "-shortest"]
    cmd += [
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
        "-movflags", "+faststart",
        str(dest),
    ]
    p = _run(cmd, timeout=3600)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg export failed: {(p.stderr or '')[-2000:]}")
    return dest


def ensure_faststart(src: Path, dest: Path) -> Path:
    """Lossless remux moving the moov atom to the front (matches SAM upload guidance)."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return src
    dest.parent.mkdir(parents=True, exist_ok=True)
    p = _run([ffmpeg, "-y", "-i", str(src), "-c", "copy", "-movflags", "+faststart", str(dest)])
    return dest if p.returncode == 0 else src
