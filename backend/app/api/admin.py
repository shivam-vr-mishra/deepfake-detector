"""Admin endpoints (read-only audit trail + blacklist management)."""
from fastapi import APIRouter, Query

from app.api.deps import AdminUser, DbSession
from app.models.audit import AuditLog
from app.models.malicious_hash import MaliciousHash
from app.security.hashing import add_to_blacklist

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit")
def list_audit(
    db: DbSession,
    _: AdminUser,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    rows = (
        db.query(AuditLog)
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(r.id),
            "user_id": str(r.user_id) if r.user_id else None,
            "event": r.event.value,
            "ip": r.ip_address,
            "user_agent": r.user_agent,
            "message": r.message,
            "metadata": r.metadata_json,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.get("/blacklist")
def list_blacklist(db: DbSession, _: AdminUser):
    rows = db.query(MaliciousHash).order_by(MaliciousHash.created_at.desc()).all()
    return [
        {
            "sha256": r.sha256,
            "reason": r.reason,
            "source": r.source,
            "created_at": r.created_at.isoformat(),
        }
        for r in rows
    ]


@router.post("/blacklist", status_code=201)
def add_blacklist(
    db: DbSession,
    _: AdminUser,
    sha256: str,
    reason: str | None = None,
    source: str | None = None,
):
    entry = add_to_blacklist(db, sha256.lower(), reason=reason, source=source)
    return {"sha256": entry.sha256, "reason": entry.reason, "source": entry.source}
