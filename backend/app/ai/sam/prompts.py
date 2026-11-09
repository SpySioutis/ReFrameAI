"""Builders for SAM 3.1 object prompts (boxes / points / masks)."""

from __future__ import annotations


def build_point_token(x: int, y: int, w: int, h: int, negative: bool = False) -> str:
    tok = f"<|point;x={x};y={y};w={w};h={h}|>"
    return f"-{tok}" if negative else tok


def build_box_token(x1: int, y1: int, x2: int, y2: int, w: int, h: int) -> str:
    return f"<|box;x1={x1};y1={y1};x2={x2};y2={y2};w={w};h={h}|>"


def build_object_prompt(
    frame: int,
    object_id: int,
    w: int,
    h: int,
    points: list[tuple[int, int, bool]] | None = None,
    box: tuple[int, int, int, int] | None = None,
) -> str:
    """Build e.g. <30f>1<|point;...|> or <0f>1<|box;...|>.

    points: list of (x, y, is_positive).
    """
    parts = [f"<{frame}f>{object_id}"]
    if box is not None:
        x1, y1, x2, y2 = box
        parts.append(build_box_token(x1, y1, x2, y2, w, h))
    for (x, y, positive) in points or []:
        parts.append(build_point_token(x, y, w, h, negative=not positive))
    return "".join(parts)


def validate_concept(concept: str) -> str:
    c = " ".join(concept.strip().split())
    if not c:
        raise ValueError("concept prompt must be a non-empty noun phrase")
    if len(c) > 120:
        raise ValueError("concept prompt too long (max 120 chars)")
    return c
