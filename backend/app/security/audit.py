"""Audit log helpers."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.audit import AuditEvent, AuditLog

log = get_logger(__name__)


def record_event(
    db: Session,
    *,
    event: AuditEvent,
    user_id: uuid.UUID | None = None,
    request: Request | None = None,
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    ip = None
    ua = None
    if request is not None:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")

    entry = AuditLog(
        user_id=user_id,
        event=event,
        ip_address=ip,
        user_agent=ua,
        message=message,
        metadata_json=metadata,
    )
    db.add(entry)
    db.commit()

    log.info(
        "audit.event",
        audit_event=event.value,
        user_id=str(user_id) if user_id else None,
        ip=ip,
        message=message,
    )
    return entry
