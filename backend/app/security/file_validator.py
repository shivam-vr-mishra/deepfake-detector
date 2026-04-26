"""File validation: extension, MIME type, size, and content sniffing.

We validate uploads on multiple layers:
1. Allowed extension by scan type
2. Allowed MIME type by scan type
3. Real MIME via libmagic (content sniffing)
4. Plan-based size limit
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import magic

from app.core.logging import get_logger
from app.models.scan import ScanType
from app.models.subscription import PlanType
from app.core.config import settings

log = get_logger(__name__)


# ---------- Allowed types per scan kind ----------
ALLOWED_EXTENSIONS: dict[ScanType, set[str]] = {
    ScanType.IMAGE: {".jpg", ".jpeg", ".png"},
    ScanType.VIDEO: {".mp4", ".mov", ".webm"},
    ScanType.AUDIO: {".mp3", ".wav", ".m4a", ".ogg", ".flac"},
    ScanType.TEXT: {".txt", ".pdf"},
}

ALLOWED_MIME: dict[ScanType, set[str]] = {
    ScanType.IMAGE: {"image/jpeg", "image/png"},
    ScanType.VIDEO: {"video/mp4", "video/quicktime", "video/webm"},
    ScanType.AUDIO: {
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/ogg",
        "audio/flac",
        "audio/m4a",
        "audio/x-m4a",
        "audio/mp4",
    },
    ScanType.TEXT: {"text/plain", "application/pdf"},
}


@dataclass
class ValidationResult:
    ok: bool
    reason: str | None = None
    mime: str | None = None
    extension: str | None = None
    size: int | None = None


class FileValidationError(Exception):
    pass


def get_plan_max_file_bytes(plan: PlanType) -> int:
    table = {
        PlanType.FREE: settings.plan_free_max_file_mb,
        PlanType.PRO: settings.plan_pro_max_file_mb,
        PlanType.ENTERPRISE: settings.plan_enterprise_max_file_mb,
    }
    return table[plan] * 1024 * 1024


def get_plan_daily_limit(plan: PlanType) -> int:
    table = {
        PlanType.FREE: settings.plan_free_daily,
        PlanType.PRO: settings.plan_pro_daily,
        PlanType.ENTERPRISE: settings.plan_enterprise_daily,
    }
    return table[plan]


def validate_extension(filename: str, scan_type: ScanType) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS[scan_type]:
        raise FileValidationError(
            f"Extension '{ext}' is not allowed for {scan_type.value}. "
            f"Allowed: {sorted(ALLOWED_EXTENSIONS[scan_type])}"
        )
    return ext


def validate_mime(declared: str | None, sniffed: str, scan_type: ScanType) -> str:
    allowed = ALLOWED_MIME[scan_type]
    if sniffed not in allowed:
        raise FileValidationError(
            f"Sniffed MIME '{sniffed}' is not allowed for {scan_type.value}. "
            f"Allowed: {sorted(allowed)}"
        )
    if declared and declared not in allowed:
        log.warning(
            "file_validator.declared_mime_mismatch",
            declared=declared,
            sniffed=sniffed,
            scan_type=scan_type.value,
        )
    return sniffed


def sniff_mime(data: bytes) -> str:
    return magic.from_buffer(data[:4096], mime=True)


def validate_size(size: int, plan: PlanType) -> None:
    max_bytes = get_plan_max_file_bytes(plan)
    if size <= 0:
        raise FileValidationError("File is empty")
    if size > max_bytes:
        raise FileValidationError(
            f"File size {size} exceeds plan limit {max_bytes} bytes "
            f"({max_bytes // (1024 * 1024)} MB)"
        )


def validate_upload(
    *,
    filename: str,
    declared_mime: str | None,
    data: bytes,
    scan_type: ScanType,
    plan: PlanType,
) -> ValidationResult:
    """Run the full validation chain."""
    try:
        ext = validate_extension(filename, scan_type)
        validate_size(len(data), plan)
        sniffed = sniff_mime(data)
        validate_mime(declared_mime, sniffed, scan_type)
    except FileValidationError as e:
        return ValidationResult(ok=False, reason=str(e))
    return ValidationResult(
        ok=True, mime=sniffed, extension=ext, size=len(data)
    )
