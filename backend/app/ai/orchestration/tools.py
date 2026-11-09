"""Allowlisted tool registry for the Muse Spark agent.

The AI may ONLY invoke these tools with Pydantic-validated arguments.
No shell execution, no arbitrary code paths.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnalyzeVideoArgs(BaseModel):
    project_id: str


class ExtractFramesArgs(BaseModel):
    project_id: str
    frame_numbers: list[int] = Field(default_factory=list, max_length=32)


class DetectObjectsArgs(BaseModel):
    project_id: str
    concept: str = Field(min_length=1, max_length=120)
    frame_number: int = Field(ge=0, default=0)


class SegmentObjectArgs(BaseModel):
    project_id: str
    frame_number: int = Field(ge=0)
    x: float
    y: float


class TrackObjectArgs(BaseModel):
    project_id: str
    object_id: str
    direction: str = Field(default="forward", pattern="^(forward|backward|both)$")


class GenerateReplacementArgs(BaseModel):
    project_id: str
    object_id: str
    prompt: str = Field(min_length=1, max_length=2000)


class RemoveObjectArgs(BaseModel):
    project_id: str
    object_id: str


class ExportVideoArgs(BaseModel):
    project_id: str
    preserve_audio: bool = True


TOOL_SCHEMAS: dict[str, type[BaseModel]] = {
    "analyze_video": AnalyzeVideoArgs,
    "extract_frames": ExtractFramesArgs,
    "detect_objects": DetectObjectsArgs,
    "segment_object": SegmentObjectArgs,
    "track_object": TrackObjectArgs,
    "generate_replacement": GenerateReplacementArgs,
    "remove_object": RemoveObjectArgs,
    "export_video": ExportVideoArgs,
}


def validate_tool_call(tool: str, args: dict[str, Any]) -> BaseModel:
    if tool not in TOOL_SCHEMAS:
        raise ValueError(f"tool '{tool}' is not allowlisted")
    return TOOL_SCHEMAS[tool].model_validate(args)


def tool_names() -> list[str]:
    return sorted(TOOL_SCHEMAS.keys())
