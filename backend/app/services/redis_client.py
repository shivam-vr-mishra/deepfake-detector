"""Redis cache helper."""
from __future__ import annotations

import json
from typing import Any

import redis

from app.core.config import settings


_pool = redis.ConnectionPool.from_url(settings.redis_url, decode_responses=True)


def get_redis() -> redis.Redis:
    return redis.Redis(connection_pool=_pool)


def cache_get_json(key: str) -> Any | None:
    raw = get_redis().get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def cache_set_json(key: str, value: Any, ttl_seconds: int = 300) -> None:
    get_redis().setex(key, ttl_seconds, json.dumps(value, default=str))
