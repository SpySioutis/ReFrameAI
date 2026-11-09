"""Pydantic request/response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field

try:
    from pydantic import EmailStr  # type: ignore[no-redef]
except Exception:  # noqa: BLE001 - optional email-validator fallback
    EmailStr = str  # type: ignore[misc,assignment]


# --- Auth ---
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# --- Projects ---
class ProjectCreate(BaseModel):
    name: str = Field(default="Untitled project", max_length=255)


class ProjectOut(BaseModel):
    id: str
    name: str
    source_video: str = ""
    thumbnail: str = ""
    duration: float = 0.0
    fps: float = 0.0
    resolution: str = ""
    status: str = "draft"
    created_at: str = ""
    updated_at: str = ""


class VideoMetadata(BaseModel):
    duration: float = 0.0
    fps: float = 0.0
    width: int = 0
    height: int = 0
    frames: int = 0
    has_audio: bool = False
    codec: str = ""


# --- Objects / segmentation ---
class PointPrompt(BaseModel):
    x: float
    y: float
    label: Literal["positive", "negative"] = "positive"


class BoxPrompt(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class SegmentRequest(BaseModel):
    frame_number: int = Field(ge=0)
    points: list[PointPrompt] = Field(default_factory=list)
    box: BoxPrompt | None = None
    concept: str = Field(default="", max_length=120)
    include_confidence: bool = False


class SegmentResponse(BaseModel):
    object_id: str
    tracking_id: int
    frame_number: int
    box: dict[str, Any]
    mask_id: str
    confidence: float | None = None
    provider: str = "sam"  # sam | local | mock
    message: str = ""


class TrackRequest(BaseModel):
    object_id: str
    start_frame: int = Field(ge=0)
    end_frame: int | None = None
    direction: Literal["forward", "backward", "both"] = "forward"


class RefineRequest(BaseModel):
    object_id: str
    frame_number: int = Field(ge=0)
    points: list[PointPrompt] = Field(default_factory=list)
    box: BoxPrompt | None = None


class DetectedObjectOut(BaseModel):
    id: str
    name: str
    tracking_id: int
    mask_count: int = 0


# --- Editing ---
class EditRequest(BaseModel):
    object_id: str | None = None
    prompt: str = Field(min_length=1, max_length=2000)
    reference_image: str = ""  # storage key of uploaded reference (optional)
    strength: float = Field(default=0.7, ge=0.0, le=1.0)
    preserve_audio: bool = True


class JobOut(BaseModel):
    id: str
    job_type: str
    status: str
    progress: float
    error_message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExportRequest(BaseModel):
    quality: Literal["preview", "high"] = "high"
    preserve_audio: bool = True


# --- Assistant ---
class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"] = "user"
    content: str


class AssistantRequest(BaseModel):
    project_id: str | None = None
    messages: list[AssistantMessage]
    frame_number: int | None = None


class AssistantResponse(BaseModel):
    reply: str
    plan: dict[str, Any] | None = None
    suggested_tool: str | None = None


# --- Providers ---
class ProviderStatus(BaseModel):
    name: str
    state: str
    message: str = ""
    model: str = ""


class ErrorResponse(BaseModel):
    detail: str
    code: str = "error"
