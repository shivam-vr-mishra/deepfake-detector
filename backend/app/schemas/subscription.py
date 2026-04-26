"""Subscription & credit schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.subscription import PlanType, SubscriptionStatus


class SubscriptionOut(BaseModel):
    id: uuid.UUID
    plan: PlanType
    status: SubscriptionStatus
    current_period_start: datetime | None
    current_period_end: datetime | None
    daily_limit: int
    max_file_mb: int
    used_today: int
    credits_balance: int = 0
    credit_price_usd: float = 0.5

    model_config = {"from_attributes": True}


class CreateSubscriptionRequest(BaseModel):
    plan: PlanType


class CreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    razorpay_key_id: str
    plan: PlanType


class VerifyPaymentRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    plan: PlanType


# ---------------- Credits ----------------
class CreditWalletOut(BaseModel):
    balance: int
    credit_price_usd: float
    min_purchase: int
    max_purchase: int


class CreditOrderRequest(BaseModel):
    credits: int = Field(..., ge=1, le=1000000)


class CreditOrderResponse(BaseModel):
    order_id: str
    amount: int  # cents
    currency: Literal["USD"] = "USD"
    credits: int
    razorpay_key_id: str


class CreditVerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    credits: int = Field(..., ge=1, le=1000000)
