"""Razorpay integration."""
from __future__ import annotations

import hashlib
import hmac
import time

import razorpay

from app.core.config import settings
from app.core.logging import get_logger
from app.models.subscription import PlanType
from app.services.plans import PLAN_PRICES_PAISE

log = get_logger(__name__)

# Razorpay caps the merchant-side `receipt` string at 40 characters, so we
# can't shove a full 36-char UUID into it. We instead derive a short, stable
# 12-character tag from the user id (hex of a SHA-1 prefix) and combine it
# with a per-call epoch suffix for uniqueness.
_RECEIPT_MAX = 40


def _short_user_tag(user_id: str) -> str:
    return hashlib.sha1(user_id.encode("utf-8")).hexdigest()[:12]


def _build_receipt(prefix: str, user_id: str, *parts: str) -> str:
    """Build a <=40 char receipt id: ``{prefix}_{tag}_{parts...}_{ts}``."""
    tag = _short_user_tag(user_id)
    ts = str(int(time.time()))[-6:]            # 6-digit rolling timestamp
    candidate = "_".join([prefix, tag, *parts, ts])
    return candidate[:_RECEIPT_MAX]


class PaymentsService:
    def __init__(self) -> None:
        self.enabled = bool(settings.razorpay_key_id and settings.razorpay_key_secret)
        if self.enabled:
            self.client = razorpay.Client(
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret)
            )
        else:
            log.warning("payments.razorpay_disabled_no_keys")
            self.client = None

    def create_order(self, plan: PlanType, user_id: str) -> dict:
        amount = PLAN_PRICES_PAISE[plan]
        if amount <= 0:
            raise ValueError("Cannot create paid order for free plan")
        if not self.enabled:
            raise RuntimeError("Razorpay is not configured")

        order = self.client.order.create(
            {
                "amount": amount,
                "currency": "INR",
                "receipt": _build_receipt("sub", user_id, plan.value),
                "notes": {"user_id": user_id, "plan": plan.value},
            }
        )
        return order

    def create_credits_order(
        self,
        *,
        num_credits: int,
        user_id: str,
    ) -> dict:
        """Create a Razorpay order for purchasing `num_credits` scan credits.

        Pricing: flat ``credit_price_usd_cents`` (default 50 cents = $0.50)
        per credit. Razorpay charges in cents (smallest USD unit).
        """
        if num_credits < settings.credit_min_purchase:
            raise ValueError(
                f"Minimum purchase is {settings.credit_min_purchase} credits"
            )
        if num_credits > settings.credit_max_purchase:
            raise ValueError(
                f"Maximum purchase is {settings.credit_max_purchase} credits"
            )
        if not self.enabled:
            raise RuntimeError("Razorpay is not configured")

        amount = settings.credit_price_usd_cents * num_credits  # cents

        order = self.client.order.create(
            {
                "amount": amount,
                "currency": "USD",
                "receipt": _build_receipt("cr", user_id, str(num_credits), "usd"),
                "notes": {
                    "user_id": user_id,
                    "type": "credits",
                    "credits": str(num_credits),
                    "currency": "USD",
                },
            }
        )
        return order

    def verify_signature(
        self, *, order_id: str, payment_id: str, signature: str
    ) -> bool:
        if not self.enabled:
            return False
        try:
            self.client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": order_id,
                    "razorpay_payment_id": payment_id,
                    "razorpay_signature": signature,
                }
            )
            return True
        except razorpay.errors.SignatureVerificationError:
            return False

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        if not settings.razorpay_webhook_secret:
            return False
        expected = hmac.new(
            settings.razorpay_webhook_secret.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)


_default: PaymentsService | None = None


def get_payments() -> PaymentsService:
    global _default
    if _default is None:
        _default = PaymentsService()
    return _default
