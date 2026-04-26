"""Authentication endpoints."""
import uuid

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from jwt import InvalidTokenError
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_email_verification_token,
    create_refresh_token,
    create_reset_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserOut,
    VerifyEmailRequest,
)
from app.security.audit import record_event
from app.security.rate_limit import limiter
from app.services.email import (
    build_email_verification_email,
    build_password_reset_email,
    send_email,
)
from app.services.plans import get_or_create_subscription

router = APIRouter(prefix="/auth", tags=["auth"])
log = get_logger(__name__)


def _queue_verification_email(
    background_tasks: BackgroundTasks, user: User
) -> None:
    """Generate a fresh verify-email token and queue the message for sending."""
    token = create_email_verification_token(user.id)
    verify_link = f"{settings.frontend_url}/verify-email?token={token}"
    text, html = build_email_verification_email(verify_link, user.full_name)
    background_tasks.add_task(
        send_email,
        to=user.email,
        subject="Verify your DeepFake Detector email",
        body=text,
        html=html,
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
def register(
    request: Request,
    payload: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
):
    user = User(
        email=payload.email.lower(),
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        is_verified=False,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    get_or_create_subscription(db, user.id)

    if settings.require_email_verification:
        _queue_verification_email(background_tasks, user)
        log.info("auth.register.verification_queued", user_id=str(user.id))
        return RegisterResponse(user=UserOut.model_validate(user))

    # Verification disabled (e.g. local dev without SMTP) — auto-mark verified.
    user.is_verified = True
    db.commit()
    db.refresh(user)
    return RegisterResponse(
        user=UserOut.model_validate(user),
        verification_required=False,
        message="Account created. You can now sign in.",
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("20/minute")
def login(request: Request, payload: LoginRequest, db: DbSession):
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        record_event(
            db,
            event=AuditEvent.LOGIN_FAILURE,
            request=request,
            message=f"Invalid credentials for {payload.email}",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        )
    if settings.require_email_verification and not user.is_verified:
        record_event(
            db,
            event=AuditEvent.LOGIN_FAILURE,
            user_id=user.id,
            request=request,
            message="Login blocked: email not verified",
        )
        # 403 + a stable detail string the frontend keys off to offer "resend".
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your inbox for the "
            "verification link or request a new one.",
        )

    record_event(db, event=AuditEvent.LOGIN_SUCCESS, user_id=user.id, request=request)

    return TokenResponse(
        access_token=create_access_token(user.id, role=user.role.value),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/verify-email", response_model=UserOut)
@limiter.limit("20/minute")
def verify_email(request: Request, payload: VerifyEmailRequest, db: DbSession):
    """Mark a user as verified given a valid email-verification token."""
    try:
        decoded = decode_token(payload.token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link",
        )
    if decoded.get("type") != "verify_email":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Wrong token type"
        )
    try:
        user_id = uuid.UUID(decoded["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid subject"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not user.is_verified:
        user.is_verified = True
        db.commit()
        db.refresh(user)
        log.info("auth.email_verified", user_id=str(user.id))

    return user


@router.post("/resend-verification", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("3/minute")
def resend_verification(
    request: Request,
    payload: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
):
    """Re-send the verification email.

    Always responds 202 — never reveals whether the email is registered.
    """
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if user and not user.is_verified and user.is_active:
        _queue_verification_email(background_tasks, user)
        log.info("auth.resend_verification", user_id=str(user.id))
    return {
        "message": "If the email is registered and unverified, a new "
        "verification link has been sent."
    }


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("60/minute")
def refresh(request: Request, body: RefreshRequest, db: DbSession):
    """Exchange a refresh token for a new access + refresh token pair.

    The refresh token is sent in the JSON body (so it never ends up in
    URLs, server logs, or browser history).
    """
    try:
        payload = decode_token(body.refresh_token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type"
        )
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid subject"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user.id, role=user.role.value),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: DbSession,
):
    user = db.query(User).filter(User.email == payload.email.lower()).first()

    # Always respond 202 — never leak account existence.
    if user:
        token = create_reset_token(user.id)
        reset_link = f"{settings.frontend_url}/reset-password?token={token}"
        text, html = build_password_reset_email(reset_link)
        background_tasks.add_task(
            send_email,
            to=user.email,
            subject="Reset your DeepFake Detector password",
            body=text,
            html=html,
        )
        record_event(
            db,
            event=AuditEvent.PASSWORD_RESET_REQUESTED,
            user_id=user.id,
            request=request,
        )
    return {"message": "If the email is registered, a reset link was sent."}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
def reset_password(request: Request, payload: ResetPasswordRequest, db: DbSession):
    try:
        decoded = decode_token(payload.token)
    except InvalidTokenError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    if decoded.get("type") != "reset":
        raise HTTPException(status_code=400, detail="Wrong token type")

    try:
        user_id = uuid.UUID(decoded["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid subject")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    record_event(
        db,
        event=AuditEvent.PASSWORD_RESET_COMPLETED,
        user_id=user.id,
        request=request,
    )
    return {"message": "Password reset successfully"}


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    """Stateless JWT logout — frontend simply discards the token.

    For full revocation, add the access token's jti to a Redis blacklist with
    the remaining TTL. Left as an extension point.
    """
    return None
