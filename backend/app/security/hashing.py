"""SHA-256 hashing & malicious-hash blacklist lookup."""
from __future__ import annotations

import hashlib

from sqlalchemy.orm import Session

from app.models.malicious_hash import MaliciousHash


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_blacklisted(db: Session, sha256: str) -> bool:
    return (
        db.query(MaliciousHash).filter(MaliciousHash.sha256 == sha256).first()
        is not None
    )


def add_to_blacklist(
    db: Session, sha256: str, reason: str | None = None, source: str | None = None
) -> MaliciousHash:
    existing = db.query(MaliciousHash).filter(MaliciousHash.sha256 == sha256).first()
    if existing:
        return existing
    entry = MaliciousHash(sha256=sha256, reason=reason, source=source)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
