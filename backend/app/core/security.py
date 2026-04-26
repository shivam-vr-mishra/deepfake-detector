"""Cryptographic primitives: password hashing & JWT helpers."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(
    subject: str | int,
    expires_delta: timedelta,
    token_type: str,
    extra: Optional[Dict[str, Any]] = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "type": token_type,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str | int, role: str = "user") -> str:
    return _create_token(
        subject,
        timedelta(minutes=settings.access_token_expire_minutes),
        "access",
        {"role": role},
    )


def create_refresh_token(subject: str | int) -> str:
    return _create_token(
        subject,
        timedelta(days=settings.refresh_token_expire_days),
        "refresh",
    )


def create_reset_token(subject: str | int) -> str:
    return _create_token(
        subject,
        timedelta(minutes=settings.password_reset_expire_minutes),
        "reset",
    )


def create_email_verification_token(subject: str | int) -> str:
    return _create_token(
        subject,
        timedelta(minutes=settings.email_verification_expire_minutes),
        "verify_email",
    )


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(
        token, settings.secret_key, algorithms=[settings.jwt_algorithm]
    )
