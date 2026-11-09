"""SAM 3.1 provider over Meta Model API Responses API.

Docs: https://dev.meta.ai/docs/sam/overview
      https://dev.meta.ai/docs/sam/segmenting
      https://dev.meta.ai/docs/sam/reading-segmentation
Auth: Bearer MODEL_API_KEY, base https://api.meta.ai/v1

Implements:
- image segmentation (concept prompt OR object prompts, never both)
- video upload (Files API) + tracked segmentation with propagation_direction
- retry with backoff, timeouts, structured errors, provider states
- graceful fallback to local CV segmentation when no credentials (labeled)
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from ...core.config import get_settings
from ...core.providers import ProviderState
from . import local as local_seg
from .parser import SegRecord, parse_output_text
from .prompts import validate_concept


class SAMError(RuntimeError):
    def __init__(self, message: str, *, code: str = "sam_error", status: int = 502):
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass
class SAMResult:
    records: list[SegRecord]
    provider: str  # "sam" | "local"
    raw_text: str = ""


def _headers() -> dict[str, str]:
    s = get_settings()
    return {"Authorization": f"Bearer {s.model_api_key}", "Content-Type": "application/json"}


def _base() -> str:
    return get_settings().model_api_base.rstrip("/")


def _request_with_retry(method: str, url: str, *, max_retries: int = 3, timeout: float = 120.0, **kwargs: Any) -> httpx.Response:
    last: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = httpx.request(method, url, timeout=timeout, **kwargs)
            if resp.status_code in (429, 502, 503, 504) and attempt < max_retries:
                time.sleep(min(2 ** attempt, 8))
                continue
            return resp
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last = e
            if attempt < max_retries:
                time.sleep(min(2 ** attempt, 8))
                continue
            raise SAMError(f"SAM request failed: {e}", code="sam_timeout")
    assert last is not None
    raise SAMError(f"SAM request failed: {last}", code="sam_unavailable")


def _extract_output_text(payload: dict[str, Any]) -> str:
    """Extract concatenated output_text from a non-streaming Responses payload."""
    texts: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        if item.get("type") == "message":
            for c in item.get("content", []):
                if isinstance(c, dict) and c.get("type") in ("output_text", "text"):
                    texts.append(str(c.get("text", "")))
        elif item.get("type") == "output_text":
            texts.append(str(item.get("text", "")))
    # Some servers also echo output_text at top level.
    if not texts and isinstance(payload.get("output_text"), str):
        texts.append(payload["output_text"])
    return "\n".join(texts)


class SAMProvider:
    name = "sam"

    def state(self) -> tuple[ProviderState, str]:
        s = get_settings()
        if not s.model_api_key.strip():
            return ProviderState.NOT_CONFIGURED, "MODEL_API_KEY is not set — using local vision fallback."
        return ProviderState.READY, f"Ready ({s.sam_model} via {s.model_api_base})."

    # -- Files API -----------------------------------------------------
    def upload_video(self, path: Path) -> str:
        s = get_settings()
        if not s.model_api_key.strip():
            raise SAMError("MODEL_API_KEY not configured", code="not_configured", status=503)
        url = f"{_base()}/files"
        with open(path, "rb") as f:
            resp = _request_with_retry(
                "POST", url,
                headers={"Authorization": f"Bearer {s.model_api_key}"},
                files={"file": (path.name, f, "video/mp4")},
                data={"purpose": "user_data"},
                timeout=300.0,
            )
        if resp.status_code != 200:
            raise SAMError(f"file upload failed ({resp.status_code}): {resp.text[:500]}", code="upload_failed")
        data = resp.json()
        fid = data.get("id", "")
        if not fid:
            raise SAMError(f"file upload returned no id: {resp.text[:300]}", code="upload_failed")
        return str(fid)

    # -- Image segmentation -------------------------------------------
    def segment_image(
        self,
        image_bytes: bytes,
        mime: str,
        *,
        concept: str = "",
        object_prompt: str = "",
        include_confidence: bool = False,
        mask_encoding: str = "one_bit",
    ) -> SAMResult:
        s = get_settings()
        if concept and object_prompt:
            raise SAMError("concept and object prompts cannot be combined", code="bad_prompt", status=400)
        if not s.model_api_key.strip():
            raise SAMError("MODEL_API_KEY not configured", code="not_configured", status=503)
        prompt_text = validate_concept(concept) if concept else object_prompt
        if not prompt_text:
            raise SAMError("a concept or object prompt is required", code="bad_prompt", status=400)
        b64 = base64.b64encode(image_bytes).decode("ascii")
        body = {
            "model": s.sam_model,
            "stream": False,
            "metadata": {"mask_encoding": mask_encoding,
                         "include_confidence": "true" if include_confidence else "false"},
            "input": [{
                "type": "message", "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt_text},
                    {"type": "input_image", "image_url": f"data:{mime};base64,{b64}"},
                ],
            }],
        }
        resp = _request_with_retry("POST", f"{_base()}/responses", headers=_headers(), json=body, timeout=180.0)
        if resp.status_code == 429:
            raise SAMError("SAM rate limited", code="rate_limited", status=429)
        if resp.status_code == 400:
            raise SAMError(f"SAM rejected request: {resp.text[:500]}", code="bad_request", status=400)
        if resp.status_code != 200:
            raise SAMError(f"SAM failed ({resp.status_code}): {resp.text[:500]}")
        text = _extract_output_text(resp.json())
        return SAMResult(records=parse_output_text(text), provider="sam", raw_text=text)

    # -- Video segmentation / tracking --------------------------------
    def segment_video(
        self,
        *,
        file_id: str = "",
        video_url: str = "",
        concept: str = "",
        object_prompt: str = "",
        propagation_direction: str = "forward",
        include_confidence: bool = False,
        mask_encoding: str = "one_bit",
    ) -> SAMResult:
        s = get_settings()
        if not s.model_api_key.strip():
            raise SAMError("MODEL_API_KEY not configured", code="not_configured", status=503)
        if concept and object_prompt:
            raise SAMError("concept and object prompts cannot be combined", code="bad_prompt", status=400)
        prompt_text = validate_concept(concept) if concept else object_prompt
        if not prompt_text:
            raise SAMError("a concept or object prompt is required", code="bad_prompt", status=400)
        if propagation_direction not in ("forward", "backward", "both"):
            raise SAMError("propagation_direction must be forward|backward|both", code="bad_prompt", status=400)
        media: dict[str, str] = {"type": "input_video"}
        if file_id:
            media["file_id"] = file_id
        elif video_url:
            media["video_url"] = video_url
        else:
            raise SAMError("file_id or video_url required", code="bad_prompt", status=400)
        body = {
            "model": s.sam_model,
            "stream": False,
            "store": False,  # long clips may exceed stored-payload limits (docs: 413)
            "metadata": {
                "mask_encoding": mask_encoding,
                "propagation_direction": propagation_direction,
                "include_confidence": "true" if include_confidence else "false",
            },
            "input": [{
                "type": "message", "role": "user",
                "content": [{"type": "input_text", "text": prompt_text}, media],
            }],
        }
        resp = _request_with_retry("POST", f"{_base()}/responses", headers=_headers(), json=body, timeout=600.0)
        if resp.status_code == 429:
            raise SAMError("SAM rate limited", code="rate_limited", status=429)
        if resp.status_code == 400:
            raise SAMError(f"SAM rejected request: {resp.text[:800]}", code="bad_request", status=400)
        if resp.status_code != 200:
            raise SAMError(f"SAM failed ({resp.status_code}): {resp.text[:800]}")
        text = _extract_output_text(resp.json())
        return SAMResult(records=parse_output_text(text), provider="sam", raw_text=text)


def segment_frame_local(
    frame_bgr: Any,
    *,
    points: list[tuple[int, int, bool]] | None = None,
    box: tuple[int, int, int, int] | None = None,
) -> Any:
    """Local fallback entry point. Returns a binary (H,W) uint8 mask."""
    import numpy as np

    if box is not None:
        mask = local_seg.segment_box(frame_bgr, *box)
    elif points:
        pos = [p for p in points if p[2]]
        if not pos:
            raise ValueError("at least one positive point is required")
        x, y, _ = pos[0]
        mask = local_seg.segment_click(frame_bgr, x, y)
        for (nx, ny, is_pos) in pos[1:] + [p for p in points if not p[2]]:
            # Additional positives union, negatives subtract (circular carve).
            import cv2

            carve = np.zeros_like(mask)
            cv2.circle(carve, (nx, ny), 20, 1, -1)
            if is_pos:
                extra = local_seg.segment_click(frame_bgr, nx, ny)
                mask = np.maximum(mask, extra)
            else:
                mask = mask * (1 - carve)
    else:
        raise ValueError("points or box required")
    return mask
