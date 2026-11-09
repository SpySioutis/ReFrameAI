"""Provider states shared by all AI integrations."""

from __future__ import annotations

from enum import Enum


class ProviderState(str, Enum):
    NOT_CONFIGURED = "not_configured"
    READY = "ready"
    PROCESSING = "processing"
    RATE_LIMITED = "rate_limited"
    FAILED = "failed"
    TEMPORARILY_UNAVAILABLE = "temporarily_unavailable"
