"""Parser for SAM 3.1 Responses-API segmentation output.

Wire grammar (docs/sam/reading-segmentation):
  line   ::= <Nf> record ("," record)*
  record ::= OBJECT_ID box mask
  box    ::= <|box;x1=..;y1=..;x2=..;y2=..;w=..;h=..[;c=..]|>
  mask   ::= <|mask;x=0;y=0[;c=..];data=H,W,enc+payload|>
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass

FRAME_RE = re.compile(r"<(\d+)f>")
BOX_RE = re.compile(r"<\|box;([^|]*)\|>")
MASK_RE = re.compile(r"<\|mask;([^|]*)\|>")
RECORD_SPLIT_RE = re.compile(r",(?=\d+<\|box;)")


def _parse_kv(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in body.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


@dataclass
class MaskPayload:
    h: int
    w: int
    encoding: str  # "~" lossless | "!" one_bit
    payload: str


@dataclass
class SegRecord:
    frame: int
    object_id: int
    box: dict[str, float]
    mask: MaskPayload
    confidence: float | None = None


def parse_output_text(text: str) -> list[SegRecord]:
    """Parse full output_text (one line per frame) into records."""
    records: list[SegRecord] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        m = FRAME_RE.match(line)
        if not m:
            continue
        frame = int(m.group(1))
        rest = line[m.end():]
        # Split on commas that start a new record (id followed by box token).
        chunks = RECORD_SPLIT_RE.split(rest)
        for chunk in chunks:
            chunk = chunk.strip()
            id_m = re.match(r"(\d+)<\|box;", chunk)
            if not id_m:
                continue
            oid = int(id_m.group(1))
            box_m = BOX_RE.search(chunk)
            mask_m = MASK_RE.search(chunk)
            if not box_m or not mask_m:
                continue
            box_kv = _parse_kv(box_m.group(1))
            mask_kv = _parse_kv(mask_m.group(1))
            try:
                box = {
                    "x1": float(box_kv["x1"]), "y1": float(box_kv["y1"]),
                    "x2": float(box_kv["x2"]), "y2": float(box_kv["y2"]),
                    "w": float(box_kv["w"]), "h": float(box_kv["h"]),
                }
            except (KeyError, ValueError):
                continue
            data = mask_kv.get("data", "")
            # data = H,W,enc+payload ; payload may itself contain , ! ~
            h_str, comma1, remainder = data.partition(",")
            w_str, comma2, enc_payload = remainder.partition(",")
            if not comma1 or not comma2 or not enc_payload:
                continue
            try:
                mh, mw = int(h_str), int(w_str)
            except ValueError:
                continue
            enc, payload = enc_payload[0], enc_payload[1:]
            conf = None
            if "c" in box_kv:
                try:
                    conf = float(box_kv["c"])
                except ValueError:
                    conf = None
            records.append(SegRecord(frame=frame, object_id=oid, box=box,
                                     mask=MaskPayload(h=mh, w=mw, encoding=enc, payload=payload),
                                     confidence=conf))
    return records


def decode_mask_raster(mask: MaskPayload) -> bytes | None:
    """Best-effort base85 decode of the mask payload.

    Returns raw decoded bytes or None. The exact bit-packing of lossless vs
    one_bit payloads is implemented by the official client libraries; this
    function only unwraps the base85 layer so callers can attempt a decode,
    and returns None when the payload is not valid base85.
    """
    try:
        # RFC1924 base85 alphabet (Python b85decode default).
        return base64.b85decode(mask.payload.encode("ascii"))  # type: ignore[call-arg]
    except Exception:
        return None


def raster_to_full_frame_mask(
    raster: bytes, mask: MaskPayload, frame_w: int, frame_h: int
) -> list[int] | None:
    """Expand a decoded one_bit raster (H*W bits, MSB-first) to full-frame mask.

    Returns a flat H_frame*W_frame list of 0/1, or None if lengths mismatch.
    Only valid when the decoded payload is a packed bitfield of H*W bits.
    """
    import math

    bits_needed = mask.h * mask.w
    bytes_needed = math.ceil(bits_needed / 8)
    if len(raster) < bytes_needed:
        return None
    small = [0] * bits_needed
    for i in range(bits_needed):
        byte = raster[i // 8]
        small[i] = (byte >> (7 - (i % 8))) & 1
    # Nearest-neighbour upscale small (mask.h x mask.w) -> frame (frame_h x frame_w).
    full = [0] * (frame_w * frame_h)
    for y in range(frame_h):
        sy = min(mask.h - 1, int(y * mask.h / max(frame_h, 1)))
        for x in range(frame_w):
            sx = min(mask.w - 1, int(x * mask.w / max(frame_w, 1)))
            full[y * frame_w + x] = small[sy * mask.w + sx]
    return full
