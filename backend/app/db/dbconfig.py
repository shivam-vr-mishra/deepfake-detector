"""Database configuration — single source of truth.

This module centralises *everything* about the database:

  * The engine (with sane pool tuning per environment)
  * The ``Base`` declarative class
  * The ``SessionLocal`` factory and ``get_db`` FastAPI dependency
  * Helpers: ``db_health()``, ``bootstrap_schema()``, ``describe()``

Both **local Docker Postgres** and **Neon (serverless Postgres)** are
supported with no code changes — the right pool/SSL/timeout settings
are picked automatically from the ``DATABASE_URL`` you put in ``.env``.

URL examples
------------

* Local dev (Docker compose)::

    DATABASE_URL=postgresql+psycopg2://deepfake:deepfake_pw@postgres:5432/deepfake_db

* Neon / RDS / any remote Postgres::

    DATABASE_URL=postgresql://USER:PASS@ep-xxx.region.aws.neon.tech/db?sslmode=require

If you need to override the auto-detection (rare), set ``DB_PROFILE`` to
``local`` or ``remote`` in ``.env``.
"""
from __future__ import annotations

import logging
import os
from typing import Generator, Literal

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

log = logging.getLogger(__name__)

DBProfile = Literal["local", "remote"]


# ---------------------------------------------------------------------------
# Profile detection
# ---------------------------------------------------------------------------

_LOCAL_HOSTS = {"", "localhost", "127.0.0.1", "::1", "postgres", "db"}


def _detect_profile(url: URL) -> DBProfile:
    """Decide whether this URL points at a local or remote Postgres.

    Honours the ``DB_PROFILE`` env var if it's set to ``local`` or ``remote``;
    otherwise infers from the host (``localhost``, the docker service name
    ``postgres``, etc. → ``local``; everything else → ``remote``).
    """
    explicit = os.getenv("DB_PROFILE", "").strip().lower()
    if explicit in {"local", "remote"}:
        return explicit  # type: ignore[return-value]

    host = (url.host or "").lower()
    return "local" if host in _LOCAL_HOSTS else "remote"


def _normalise_url(raw_url: str) -> URL:
    """Upgrade ``postgresql://`` to ``postgresql+psycopg2://`` so the driver
    is explicit (avoids SQLAlchemy 2.x deprecation warnings)."""
    url = make_url(raw_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg2")
    return url


# ---------------------------------------------------------------------------
# Engine builder
# ---------------------------------------------------------------------------


def _build_engine(raw_url: str) -> tuple[Engine, DBProfile, URL]:
    """Build a SQLAlchemy engine with profile-appropriate settings."""
    url = _normalise_url(raw_url)
    profile = _detect_profile(url)
    is_postgres = url.get_backend_name() == "postgresql"

    connect_args: dict = {}
    pool_kwargs: dict = {}

    if is_postgres:
        # Always set a sane connect timeout so cold-start (Neon) or DNS
        # issues don't hang request handlers.
        connect_args["connect_timeout"] = 10

        if profile == "remote":
            # Neon / RDS / any managed Postgres:
            #   * Force TLS — managed providers refuse plaintext.
            #   * Smaller pool — Neon free tier caps at ~100 conns and we
            #     run 1 backend + N celery workers.
            #   * Recycle connections every 5 min — Neon scales compute to
            #     zero, which kills idle TCP sessions; recycling avoids
            #     surprises and ``pool_pre_ping`` covers anything that slips.
            existing_query = dict(url.query or {})
            if "sslmode" not in existing_query:
                connect_args["sslmode"] = "require"
            pool_kwargs.update(
                pool_size=10,
                max_overflow=10,
                pool_recycle=300,
                pool_pre_ping=True,
                pool_use_lifo=True,
            )
        else:
            # Local docker Postgres — generous pool, no recycle needed.
            pool_kwargs.update(
                pool_size=20,
                max_overflow=20,
                pool_pre_ping=True,
            )

    engine = create_engine(
        url,
        future=True,
        connect_args=connect_args,
        **pool_kwargs,
    )

    log.info(
        "db.engine.ready profile=%s host=%s db=%s pool_size=%s",
        profile,
        url.host or "(socket)",
        url.database,
        pool_kwargs.get("pool_size", "default"),
    )
    return engine, profile, url


engine, DB_PROFILE, _DB_URL = _build_engine(settings.database_url)


# ---------------------------------------------------------------------------
# Session + Base
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True
)


class Base(DeclarativeBase):
    """Declarative base for every ORM model in the project."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def db_health() -> dict:
    """Lightweight ping for ``/health`` endpoints / readiness probes."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "profile": DB_PROFILE, "host": _DB_URL.host}
    except Exception as exc:  # pragma: no cover - reported, not raised
        log.warning("db.health.failed err=%s", exc)
        return {"ok": False, "profile": DB_PROFILE, "host": _DB_URL.host, "error": str(exc)}


def bootstrap_schema() -> None:
    """Create all ORM tables.

    * In **local** mode, also acquires a Postgres advisory lock so that
      multiple Uvicorn workers running ``create_all`` concurrently don't
      race on enum/type creation.
    * In **remote** mode, the lock is skipped because production is
      expected to use Alembic migrations and call this only once during
      a controlled bootstrap step.

    Importing here (lazy) avoids a circular dependency between this
    module and ``app.models`` (which imports ``Base`` from us).
    """
    import app.models  # noqa: F401  -- registers all ORM models on Base.metadata

    advisory_lock_id = 0x4445_4546_414B_4521  # "DEEPFAKE!"

    with engine.begin() as conn:
        if DB_PROFILE == "local" and _DB_URL.get_backend_name() == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": advisory_lock_id})
        Base.metadata.create_all(bind=conn)
    log.info("db.schema.bootstrapped profile=%s", DB_PROFILE)


def describe() -> dict:
    """Human-readable summary of the active DB config (for /admin/diagnostics)."""
    return {
        "profile": DB_PROFILE,
        "driver": _DB_URL.drivername,
        "host": _DB_URL.host,
        "port": _DB_URL.port,
        "database": _DB_URL.database,
        "ssl": "sslmode" in (_DB_URL.query or {}) or DB_PROFILE == "remote",
    }


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
