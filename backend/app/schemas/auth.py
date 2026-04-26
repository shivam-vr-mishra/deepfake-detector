"""Auth-related Pydantic schemas."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class VerifyEmailRequest(BaseModel):
    token: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class RegisterResponse(BaseModel):
    """Returned by /auth/register.

    We deliberately do **not** issue an access token here — the user must
    confirm ownership of their email first.
    """

    user: "UserOut"
    verification_required: bool = True
    message: str = (
        "Account created. Please check your email to verify your address "
        "before signing in."
    )


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool

    model_config = {"from_attributes": True}


# Resolve forward reference for RegisterResponse.user
RegisterResponse.model_rebuild()
