"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, AnyHttpUrl, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "DeepFake Detector"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    # Security
    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    password_reset_expire_minutes: int = 30
    email_verification_expire_minutes: int = 60 * 24  # 24h
    # If True, /auth/login is rejected for users with is_verified=False.
    # Toggle this off only for local debugging without SMTP.
    require_email_verification: bool = True

    # ---------------- Database ----------------
    # Two URLs are kept side-by-side; ``db_target`` decides which one is active.
    #   db_target=neon  -> use DATABASE_URL_NEON   (default)
    #   db_target=local -> use DATABASE_URL_LOCAL
    # If DATABASE_URL is set explicitly, it overrides both (manual override).
    db_target: str = "neon"
    database_url_local: str = (
        "postgresql+psycopg2://deepfake:deepfake_pw@postgres:5432/deepfake_db"
    )
    database_url_neon: str = ""
    database_url: str = ""

    @model_validator(mode="after")
    def _resolve_database_url(self) -> "Settings":
        # Highest precedence: explicit DATABASE_URL in env.
        if self.database_url.strip():
            return self
        target = (self.db_target or "neon").strip().lower()
        if target == "local":
            self.database_url = self.database_url_local
        elif target == "neon":
            if not self.database_url_neon.strip():
                raise RuntimeError(
                    "DB_TARGET=neon but DATABASE_URL_NEON is empty. "
                    "Set DATABASE_URL_NEON in your .env or switch DB_TARGET=local."
                )
            self.database_url = self.database_url_neon
        else:
            raise RuntimeError(
                f"Unknown DB_TARGET={self.db_target!r}. "
                "Use 'neon' or 'local' (or set DATABASE_URL explicitly)."
            )
        return self

    # Redis & Celery
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # MinIO
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "deepfake-uploads"
    minio_secure: bool = False

    # ClamAV
    clamav_host: str = "clamav"
    clamav_port: int = 3310
    clamav_timeout: int = 60

    # SMTP
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "no-reply@deepfake-detector.app"
    smtp_tls: bool = True

    # Razorpay
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""

    # Plan limits
    plan_free_daily: int = 1
    plan_free_max_file_mb: int = 10
    plan_pro_daily: int = 500
    plan_pro_max_file_mb: int = 200
    plan_enterprise_daily: int = 10000
    plan_enterprise_max_file_mb: int = 2048

    # Pay-per-scan credit pricing
    # 1 credit = 1 scan; flat $0.50 (50 cents) globally.
    credit_price_usd_cents: int = 50
    credit_min_purchase: int = 10
    credit_max_purchase: int = 100000

    # Rate limiting
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 120

    @property
    def cors_origins(self) -> List[str]:
        return [self.frontend_url, "http://localhost:3000"]

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
