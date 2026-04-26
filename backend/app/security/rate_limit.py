"""Per-user + per-IP rate limiting using slowapi (Redis-backed)."""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def identity_key(request: Request) -> str:
    """Use the authenticated user id when available, otherwise client IP.

    The auth dependency stores the user id in ``request.state.user_id`` after
    a successful JWT validation. Falling back to IP for anonymous endpoints
    (login/register) keeps the limiter useful against credential stuffing.
    """
    user_id = getattr(request.state, "user_id", None)
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


# headers_enabled=False because slowapi's per-route @limiter.limit decorator
# trips over response-header injection when the endpoint returns a Pydantic
# model (it expects an explicit Response parameter). The middleware-level
# enforcement still applies the limits.
limiter = Limiter(
    key_func=identity_key,
    storage_uri=settings.redis_url,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
    headers_enabled=False,
)
