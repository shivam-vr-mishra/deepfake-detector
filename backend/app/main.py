"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import admin, auth, detection, history, subscription
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.db import DB_PROFILE, bootstrap_schema, db_health
from app.security.rate_limit import limiter

configure_logging("DEBUG" if settings.app_debug else "INFO")
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.services.email import smtp_config_summary

    log.info("app.starting", env=settings.app_env, db_profile=DB_PROFILE)
    if not settings.is_production:
        bootstrap_schema()

    smtp = smtp_config_summary()
    if not smtp["configured"]:
        log.warning(
            "smtp.not_configured",
            require_email_verification=settings.require_email_verification,
            hint="SMTP_USER/SMTP_PASSWORD are empty -- verification emails "
            "will be skipped. New users will not be able to sign in while "
            "REQUIRE_EMAIL_VERIFICATION=true.",
        )
    else:
        log.info("smtp.configured", **{k: smtp[k] for k in ("host", "port", "user", "from", "tls")})

    yield
    log.info("app.stopping")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.app_debug,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------- Middleware ----------------
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- Exception handlers ----------------
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )


# ---------------- Routes ----------------
@app.get("/", tags=["meta"])
def root():
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "ok",
        "docs": "/docs",
    }


@app.get("/health", tags=["meta"])
def health():
    from app.security.virus_scanner import get_virus_scanner
    from app.services.email import smtp_config_summary

    db = db_health()
    smtp = smtp_config_summary()
    return {
        "status": "ok" if db["ok"] else "degraded",
        "db": db,
        "clamav": get_virus_scanner().ping(),
        "smtp": {
            "configured": smtp["configured"],
            "host": smtp["host"],
            "port": smtp["port"],
            "user": smtp["user"],
            "tls": smtp["tls"],
        },
        "require_email_verification": settings.require_email_verification,
    }


app.include_router(auth.router)
app.include_router(detection.router)
app.include_router(history.router)
app.include_router(subscription.router)
app.include_router(admin.router)
