"""Muse Spark 1.3 orchestration client.

Docs: https://dev.meta.ai/docs/muse-spark
Model: muse-spark-1.3, base https://api.meta.ai/v1
Protocols: Responses / Chat Completions / Messages. We use Chat Completions
(OpenAI-compatible) for tool calling, with max reasoning effort for planning.

When MODEL_API_KEY is missing, `plan_locally` provides a deterministic
rule-based fallback so the assistant UI and job pipeline remain testable.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from ...core.config import get_settings
from ...core.providers import ProviderState


class SparkError(RuntimeError):
    def __init__(self, message: str, *, code: str = "spark_error", status: int = 502):
        super().__init__(message)
        self.code = code
        self.status = status


@dataclass
class SparkPlan:
    operation: str  # remove|replace|restyle|detect|unknown
    target: str
    prompt: str
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    needs_clarification: bool = False
    question: str = ""


SYSTEM_PROMPT = """You are ReFrameAI's editing planner. Convert a user's video-editing \
instruction into a structured plan. Output STRICT JSON only with keys: \
operation (remove|replace|restyle|detect|unknown), target (short noun phrase of the \
object), prompt (detailed generation prompt preserving lighting/shadows/perspective), \
tool (one of: remove_object, generate_replacement, restyle_object, detect_objects, \
segment_object, track_object, export_video), args (object with optional keys: \
frame_number, concept, strength), needs_clarification (boolean), \
question (clarifying question when ambiguous, else empty string).
Rules: ask for clarification when the target object or operation is ambiguous. \
Never invent file paths. Never output shell commands."""


def plan_locally(text: str) -> SparkPlan:
    """Deterministic fallback planner (no network)."""
    t = text.lower().strip()
    if any(w in t for w in ("remove", "delete", "erase", "take out", "αφαίρε", "διαγρα")):
        target = _guess_target(t, ["remove", "delete", "erase"])
        return SparkPlan(operation="remove", target=target, prompt=text.strip(),
                         tool="remove_object", args={})
    if any(w in t for w in ("replace", "swap", "change", "αντικατ")):
        return SparkPlan(operation="replace", target=_guess_target(t, ["replace", "swap"]),
                         prompt=text.strip(), tool="generate_replacement", args={})
    if any(w in t for w in ("restyle", "style", "cartoon", "anime", "στικ", "στυλ")):
        return SparkPlan(operation="restyle", target=_guess_target(t, ["restyle", "style"]),
                         prompt=text.strip(), tool="restyle_object", args={})
    if any(w in t for w in ("detect", "find", "segment", "select", "εντοπ", "επίλε")):
        return SparkPlan(operation="detect", target=_guess_target(t, ["detect", "find", "segment"]),
                         prompt=text.strip(), tool="detect_objects", args={})
    return SparkPlan(operation="unknown", target="", prompt=text.strip(), tool="segment_object",
                     needs_clarification=True,
                     question="Which object should I edit, and should I remove, replace, or restyle it?")


def _guess_target(t: str, verbs: list[str]) -> str:
    for v in verbs:
        if v in t:
            rest = t.split(v, 1)[1].strip(" .,:\"'")
            for stop in (" in ", " from ", " with ", " and ", " please"):
                rest = rest.split(stop)[0]
            if rest:
                return rest[:80]
    return ""


class MuseSparkProvider:
    name = "muse_spark"

    def state(self) -> tuple[ProviderState, str]:
        s = get_settings()
        if not s.model_api_key.strip():
            return ProviderState.NOT_CONFIGURED, "MODEL_API_KEY is not set — rule-based planner active."
        return ProviderState.READY, f"Ready ({s.spark_model}, max reasoning)."

    def plan(self, user_text: str, *, context: str = "") -> SparkPlan:
        s = get_settings()
        if not s.model_api_key.strip():
            return plan_locally(user_text)
        body = {
            "model": s.spark_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"{context}\n\nInstruction: {user_text}".strip()},
            ],
            "response_format": {"type": "json_object"},
        }
        last: Exception | None = None
        for attempt in range(3):
            try:
                resp = httpx.post(
                    f"{s.model_api_base.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {s.model_api_key}",
                             "Content-Type": "application/json"},
                    json=body, timeout=120.0,
                )
                if resp.status_code in (429, 502, 503, 504) and attempt < 2:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                if resp.status_code != 200:
                    raise SparkError(f"Muse Spark failed ({resp.status_code}): {resp.text[:400]}")
                content = resp.json()["choices"][0]["message"]["content"]
                data = json.loads(content)
                return SparkPlan(
                    operation=str(data.get("operation", "unknown")),
                    target=str(data.get("target", "")),
                    prompt=str(data.get("prompt", user_text)),
                    tool=str(data.get("tool", "segment_object")),
                    args=dict(data.get("args", {})),
                    needs_clarification=bool(data.get("needs_clarification", False)),
                    question=str(data.get("question", "")),
                )
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last = e
                time.sleep(min(2 ** attempt, 8))
        raise SparkError(f"Muse Spark request failed: {last}")

    def chat(self, messages: list[dict[str, str]], *, context: str = "") -> str:
        s = get_settings()
        if not s.model_api_key.strip():
            plan = plan_locally(messages[-1]["content"] if messages else "")
            if plan.needs_clarification:
                return plan.question
            return (f"I'll {plan.operation} '{plan.target or 'the selected object'}'. "
                    f"Select the object in the editor, then run the {plan.operation} job. "
                    "(Local planner — set MODEL_API_KEY for full Muse Spark reasoning.)")
        body = {
            "model": s.spark_model,
            "messages": ([{"role": "system", "content": (
                "You are ReFrameAI's video-editing assistant. Help the user select objects "
                "and describe remove/replace/restyle edits. Be concise. "
                f"Project context: {context}" if context else
                "You are ReFrameAI's video-editing assistant. Be concise.")}]
                + messages[-12:]),
        }
        resp = httpx.post(
            f"{s.model_api_base.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {s.model_api_key}", "Content-Type": "application/json"},
            json=body, timeout=120.0,
        )
        if resp.status_code != 200:
            raise SparkError(f"Muse Spark failed ({resp.status_code}): {resp.text[:400]}")
        return str(resp.json()["choices"][0]["message"]["content"])
