"""Detection-related schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from app.models.scan import ScanStatus, ScanType


class TextDetectRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)


class UrlDetectRequest(BaseModel):
    url: HttpUrl


class DetectionResult(BaseModel):
    score: float = Field(ge=0.0, le=1.0)
    label: str
    explanation: str
    confidence: str


class ScanOut(BaseModel):
    id: uuid.UUID
    scan_type: ScanType
    status: ScanStatus
    original_filename: str | None
    mime_type: str | None
    file_size: int | None
    source_url: str | None
    score: float | None
    label: str | None
    confidence: str | None
    explanation: str | None
    result_payload: dict[str, Any] | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ScanCreatedResponse(BaseModel):
    scan_id: uuid.UUID
    status: ScanStatus
    message: str = "Scan queued for processing"
