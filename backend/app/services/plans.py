"""Plan limits, daily usage, and pay-per-scan credit wallet."""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.credit_wallet import CreditWallet
from app.models.subscription import PlanType, Subscription, SubscriptionStatus
from app.models.usage import UsageRecord
from app.security.file_validator import (
    get_plan_daily_limit,
    get_plan_max_file_bytes,
)


# Razorpay amounts in *paise* (INR). 1 INR = 100 paise.
PLAN_PRICES_PAISE: dict[PlanType, int] = {
    PlanType.FREE: 0,
    PlanType.PRO: 99900,        # ₹999/month
    PlanType.ENTERPRISE: 499900,  # ₹4999/month
}


# ---------------- Subscription ----------------
def get_or_create_subscription(db: Session, user_id: uuid.UUID) -> Subscription:
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if sub:
        return sub
    sub = Subscription(
        user_id=user_id,
        plan=PlanType.FREE,
        status=SubscriptionStatus.ACTIVE,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


# ---------------- Daily usage ----------------
def get_today_usage(db: Session, user_id: uuid.UUID) -> int:
    today = date.today()
    rec = (
        db.query(UsageRecord)
        .filter(UsageRecord.user_id == user_id, UsageRecord.day == today)
        .first()
    )
    return rec.count if rec else 0


def increment_usage(db: Session, user_id: uuid.UUID) -> int:
    today = date.today()
    rec = (
        db.query(UsageRecord)
        .filter(UsageRecord.user_id == user_id, UsageRecord.day == today)
        .with_for_update()
        .first()
    )
    if rec is None:
        rec = UsageRecord(user_id=user_id, day=today, count=1)
        db.add(rec)
    else:
        rec.count += 1
    db.commit()
    db.refresh(rec)
    return rec.count


def check_quota(
    db: Session, user_id: uuid.UUID, plan: PlanType
) -> tuple[bool, int, int]:
    used = get_today_usage(db, user_id)
    limit = get_plan_daily_limit(plan)
    return used < limit, used, limit


# ---------------- Credit wallet ----------------
def get_or_create_wallet(db: Session, user_id: uuid.UUID) -> CreditWallet:
    wallet = (
        db.query(CreditWallet).filter(CreditWallet.user_id == user_id).first()
    )
    if wallet:
        return wallet
    wallet = CreditWallet(user_id=user_id, balance=0)
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet


def get_credit_balance(db: Session, user_id: uuid.UUID) -> int:
    wallet = get_or_create_wallet(db, user_id)
    return wallet.balance


def add_credits(db: Session, user_id: uuid.UUID, amount: int) -> int:
    """Atomically add `amount` credits to user wallet. Returns new balance."""
    if amount <= 0:
        raise ValueError("amount must be positive")
    get_or_create_wallet(db, user_id)
    wallet = (
        db.query(CreditWallet)
        .filter(CreditWallet.user_id == user_id)
        .with_for_update()
        .one()
    )
    wallet.balance += amount
    db.commit()
    db.refresh(wallet)
    return wallet.balance


def consume_credit(db: Session, user_id: uuid.UUID, amount: int = 1) -> bool:
    """Atomically consume `amount` credits. Returns True on success."""
    if amount <= 0:
        return True
    get_or_create_wallet(db, user_id)
    wallet = (
        db.query(CreditWallet)
        .filter(CreditWallet.user_id == user_id)
        .with_for_update()
        .one()
    )
    if wallet.balance < amount:
        db.commit()
        return False
    wallet.balance -= amount
    db.commit()
    db.refresh(wallet)
    return True


# ---------------- Combined gate ----------------
def reserve_scan(
    db: Session, user_id: uuid.UUID, plan: PlanType
) -> tuple[bool, str]:
    """Reserve one scan against the daily free quota first, then credits.

    Returns (ok, source) where `source` ∈ {"free", "credit", "denied"}.
    On success the caller should call `increment_usage(db, user_id)` after the
    scan row has been created (matches existing semantics).
    """
    ok, _used, _limit = check_quota(db, user_id, plan)
    if ok:
        return True, "free"
    if consume_credit(db, user_id, 1):
        return True, "credit"
    return False, "denied"


# ---------------- Plan / pricing summaries ----------------
def plan_summary(plan: PlanType) -> dict:
    return {
        "plan": plan.value,
        "daily_limit": get_plan_daily_limit(plan),
        "max_file_mb": get_plan_max_file_bytes(plan) // (1024 * 1024),
        "price_paise": PLAN_PRICES_PAISE[plan],
        "price_inr": PLAN_PRICES_PAISE[plan] / 100,
    }


def credit_pricing() -> dict:
    return {
        "credit_price_usd": settings.credit_price_usd_cents / 100,
        "credit_price_usd_cents": settings.credit_price_usd_cents,
        "min_purchase": settings.credit_min_purchase,
        "max_purchase": settings.credit_max_purchase,
    }
