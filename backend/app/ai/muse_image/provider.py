"""Muse Image 1.0 provider.

Docs: https://dev.meta.ai/docs/image-generation
Model: muse-image-1.0
Endpoints: POST /v1/images/generations (text-to-image)
           POST /v1/images/edits (image edit; JSON body with images[] for raw HTTP)

IMPORTANT (verified in docs): the edits endpoint does NOT accept a `mask`
parameter (returns 400 unsupported_parameter). Mask-conditioned editing is
therefore implemented as an intermediate pipeline in `services/edit_service`:
crop/zoom around the object -> edit -> composite back with feathered mask.
"""

from __future__ import annotations

import base64
import time
from dataclasses import dataclass

import httpx

from ...core.config import get_settings
from ...core.providers import ProviderState


class ImageError(RuntimeError):
    def __init__(self, message: str, *, code: str = "image_error", status: int = 502):
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass
class GeneratedImage:
    data: bytes
    mime: str = "image/webp"


def _base() -> str:
    return get_settings().model_api_base.rstrip("/")


def _headers() -> dict[str, str]:
    s = get_settings()
    return {"Authorization": f"Bearer {s.model_api_key}", "Content-Type": "application/json"}


def _post(path: str, body: dict, timeout: float = 300.0) -> dict:
    s = get_settings()
    if not s.model_api_key.strip():
        raise ImageError("MODEL_API_KEY not configured", code="not_configured", status=503)
    last: Exception | None = None
    for attempt in range(4):
        try:
            resp = httpx.post(f"{_base()}{path}", headers=_headers(), json=body, timeout=timeout)
            if resp.status_code in (429, 502, 503, 504) and attempt < 3:
                time.sleep(min(2 ** attempt, 8))
                continue
            if resp.status_code == 429:
                raise ImageError("Muse Image rate limited", code="rate_limited", status=429)
            if resp.status_code == 400:
                raise ImageError(f"Muse Image rejected request: {resp.text[:600]}", code="bad_request", status=400)
            if resp.status_code != 200:
                raise ImageError(f"Muse Image failed ({resp.status_code}): {resp.text[:600]}")
            return resp.json()
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            last = e
            time.sleep(min(2 ** attempt, 8))
    raise ImageError(f"Muse Image request failed: {last}", code="image_unavailable")


def _first_image(payload: dict) -> GeneratedImage:
    data = payload.get("data", [])
    if not data:
        raise ImageError("Muse Image returned no images", code="empty_result")
    entry = data[0]
    if entry.get("b64_json"):
        raw = base64.b64decode(entry["b64_json"])
        fmt = payload.get("output_format", "webp")
        mime = {"webp": "image/webp", "png": "image/png", "jpeg": "image/jpeg"}.get(fmt, "image/webp")
        return GeneratedImage(data=raw, mime=mime)
    if entry.get("url"):
        r = httpx.get(entry["url"], timeout=120.0)
        r.raise_for_status()
        return GeneratedImage(data=r.content, mime=r.headers.get("content-type", "image/webp"))
    raise ImageError("Muse Image returned an unrecognized payload", code="empty_result")


class MuseImageProvider:
    name = "muse_image"

    def state(self) -> tuple[ProviderState, str]:
        s = get_settings()
        if not s.model_api_key.strip():
            return ProviderState.NOT_CONFIGURED, "MODEL_API_KEY is not set — generative replace/restyle unavailable."
        return ProviderState.READY, f"Ready ({s.image_model})."

    def generate(self, prompt: str, *, size: str = "", reasoning: str = "high") -> GeneratedImage:
        s = get_settings()
        body: dict = {"model": s.image_model, "prompt": prompt.strip(), "n": 1}
        if size:
            body["size"] = size
        if reasoning in ("low", "high"):
            body["reasoning_strength"] = reasoning
        return _first_image(_post("/images/generations", body))

    def edit(
        self,
        prompt: str,
        images_b64: list[tuple[str, str]],
        *,
        size: str = "",
        reasoning: str = "high",
    ) -> GeneratedImage:
        """Edit one or more images.

        images_b64: list of (mime, base64) tuples, sent as images[].image_url data URLs.
        """
        s = get_settings()
        if not 1 <= len(images_b64) <= 10:
            raise ImageError("edits need 1-10 input images", code="bad_request", status=400)
        body: dict = {
            "model": s.image_model,
            "prompt": prompt.strip(),
            "images": [{"image_url": f"data:{mime};base64,{b64}"} for mime, b64 in images_b64],
            "n": 1,
        }
        if size:
            body["size"] = size
        if reasoning in ("low", "high"):
            body["reasoning_strength"] = reasoning
        return _first_image(_post("/images/edits", body))

    def build_replacement_prompt(
        self,
        user_prompt: str,
        *,
        operation: str,
        scene_context: str = "",
    ) -> str:
        """Wrap the user instruction with preservation requirements."""
        preserve = (
            "Preserve the original perspective, camera angle, lighting direction, "
            "shadows, reflections, object scale, and environmental context. "
            "Photorealistic, seamless blend with the surrounding scene."
        )
        if operation == "remove":
            base = f"Remove the masked object completely and reconstruct the background naturally. {preserve}"
        elif operation == "restyle":
            base = f"Restyle the masked object as follows: {user_prompt}. {preserve}"
        else:
            base = f"Replace the masked object as follows: {user_prompt}. {preserve}"
        if scene_context:
            base += f" Scene context: {scene_context}."
        return base
