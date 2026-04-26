"""Backwards-compatibility shim.

All database configuration now lives in :mod:`app.db.dbconfig`. This module
simply re-exports the public names so existing ``from app.db.session import …``
imports continue to work without changes.

Prefer importing from ``app.db.dbconfig`` (or ``app.db``) in new code.
"""
from app.db.dbconfig import (  # noqa: F401
    Base,
    DB_PROFILE,
    SessionLocal,
    bootstrap_schema,
    db_health,
    describe,
    engine,
    get_db,
)

__all__ = [
    "Base",
    "DB_PROFILE",
    "SessionLocal",
    "bootstrap_schema",
    "db_health",
    "describe",
    "engine",
    "get_db",
]
