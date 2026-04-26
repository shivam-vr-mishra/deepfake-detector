"""Subscription endpoints, monthly plans, and pay-per-scan credits."""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.core.logging import get_logger
from app.models.audit import AuditEvent
from app.models.subscription import PlanType, SubscriptionStatus
from app.schemas.subscription import (
    CreateOrderResponse,
    CreateSubscriptionRequest,
    CreditOrderRequest,
    CreditOrderResponse,
    CreditVerifyRequest,
    CreditWalletOut,
    SubscriptionOut,
    VerifyPaymentRequest,
)
from app.security.audit import record_event
from app.security.file_validator import (
    get_plan_daily_limit,
    get_plan_max_file_bytes,
)
from app.services.payments import get_payments
from app.services.plans import (
    PLAN_PRICES_PAISE,
    add_credits,
    credit_pricing,
    get_credit_balance,
    get_or_create_subscription,
    get_or_create_wallet,
    get_today_usage,
    plan_summary,
)

router = APIRouter(prefix="/subscription", tags=["subscription"])
log = get_logger(__name__)


def _serialize(sub, used: int, credits_balance: int) -> SubscriptionOut:
    return SubscriptionOut(
        id=sub.id,
        plan=sub.plan,
        status=sub.status,
        current_period_start=sub.current_period_start,
        current_period_end=sub.current_period_end,
        daily_limit=get_plan_daily_limit(sub.plan),
        max_file_mb=get_plan_max_file_bytes(sub.plan) // (1024 * 1024),
        used_today=used,
        credits_balance=credits_balance,
        credit_price_usd=settings.credit_price_usd_cents / 100,
    )


@router.get("", response_model=SubscriptionOut)
def get_subscription(db: DbSession, user: CurrentUser):
    sub = get_or_create_subscription(db, user.id)
    used = get_today_usage(db, user.id)
    balance = get_credit_balance(db, user.id)
    return _serialize(sub, used, balance)


@router.get("/plans")
def list_plans():
    return [plan_summary(p) for p in PlanType]


# -----------------------------------------------------------
# Monthly plan checkout (existing flow)
# -----------------------------------------------------------
@router.post("/order", response_model=CreateOrderResponse)
def create_order(
    payload: CreateSubscriptionRequest,
    db: DbSession,
    user: CurrentUser,
):
    if payload.plan == PlanType.FREE:
        raise HTTPException(status_code=400, detail="Cannot order the free plan")
    payments = get_payments()
    if not payments.enabled:
        raise HTTPException(status_code=503, detail="Payments not configured")

    order = payments.create_order(payload.plan, str(user.id))
    return CreateOrderResponse(
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        razorpay_key_id=settings.razorpay_key_id,
        plan=payload.plan,
    )


@router.post("/verify", response_model=SubscriptionOut)
def verify_payment(
    request: Request,
    payload: VerifyPaymentRequest,
    db: DbSession,
    user: CurrentUser,
):
    payments = get_payments()
    if not payments.verify_signature(
        order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    ):
        raise HTTPException(status_code=400, detail="Invalid signature")

    sub = get_or_create_subscription(db, user.id)
    sub.plan = payload.plan
    sub.status = SubscriptionStatus.ACTIVE
    sub.current_period_start = datetime.now(timezone.utc)
    sub.current_period_end = sub.current_period_start + timedelta(days=30)
    db.commit()
    db.refresh(sub)

    record_event(
        db,
        event=AuditEvent.SUBSCRIPTION_CREATED,
        user_id=user.id,
        request=request,
        message=f"Upgraded to {payload.plan.value}",
        metadata={
            "order_id": payload.razorpay_order_id,
            "payment_id": payload.razorpay_payment_id,
        },
    )
    return _serialize(
        sub, get_today_usage(db, user.id), get_credit_balance(db, user.id)
    )


@router.post("/cancel", response_model=SubscriptionOut)
def cancel_subscription(request: Request, db: DbSession, user: CurrentUser):
    sub = get_or_create_subscription(db, user.id)
    sub.status = SubscriptionStatus.CANCELLED
    sub.plan = PlanType.FREE
    db.commit()
    db.refresh(sub)
    record_event(
        db,
        event=AuditEvent.SUBSCRIPTION_CANCELLED,
        user_id=user.id,
        request=request,
    )
    return _serialize(
        sub, get_today_usage(db, user.id), get_credit_balance(db, user.id)
    )


# -----------------------------------------------------------
# Pay-per-scan credits
# -----------------------------------------------------------
@router.get("/credits", response_model=CreditWalletOut)
def get_credits(db: DbSession, user: CurrentUser):
    wallet = get_or_create_wallet(db, user.id)
    pricing = credit_pricing()
    return CreditWalletOut(
        balance=wallet.balance,
        credit_price_usd=pricing["credit_price_usd"],
        min_purchase=pricing["min_purchase"],
        max_purchase=pricing["max_purchase"],
    )


@router.post("/credits/order", response_model=CreditOrderResponse)
def create_credits_order(
    payload: CreditOrderRequest,
    db: DbSession,
    user: CurrentUser,
):
    payments = get_payments()
    if not payments.enabled:
        raise HTTPException(status_code=503, detail="Payments not configured")

    try:
        order = payments.create_credits_order(
            num_credits=payload.credits,
            user_id=str(user.id),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CreditOrderResponse(
        order_id=order["id"],
        amount=order["amount"],
        currency="USD",
        credits=payload.credits,
        razorpay_key_id=settings.razorpay_key_id,
    )


@router.post("/credits/verify", response_model=CreditWalletOut)
def verify_credits_payment(
    request: Request,
    payload: CreditVerifyRequest,
    db: DbSession,
    user: CurrentUser,
):
    payments = get_payments()
    if not payments.verify_signature(
        order_id=payload.razorpay_order_id,
        payment_id=payload.razorpay_payment_id,
        signature=payload.razorpay_signature,
    ):
        raise HTTPException(status_code=400, detail="Invalid signature")

    new_balance = add_credits(db, user.id, payload.credits)

    record_event(
        db,
        event=AuditEvent.CREDITS_PURCHASED,
        user_id=user.id,
        request=request,
        message=f"+{payload.credits} credits (USD)",
        metadata={
            "order_id": payload.razorpay_order_id,
            "payment_id": payload.razorpay_payment_id,
            "credits": payload.credits,
            "currency": "USD",
        },
    )

    pricing = credit_pricing()
    return CreditWalletOut(
        balance=new_balance,
        credit_price_usd=pricing["credit_price_usd"],
        min_purchase=pricing["min_purchase"],
        max_purchase=pricing["max_purchase"],
    )
