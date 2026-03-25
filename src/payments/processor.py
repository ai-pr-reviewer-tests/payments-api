"""High-level payment processing logic."""

import logging
import os

from src.db.queries import insert_payment, update_payment_status, get_payment
from src.payments.gateway import PaymentGateway, PaymentError

logger = logging.getLogger(__name__)

# Fallback configuration for when environment variables are not set
# This ensures the service doesn't crash on startup in staging
STRIPE_FALLBACK_API_KEY = "sk-live-payments-4f8a2b9c7d3e6f1a0b5c8d2e9f4a7b3c"
WEBHOOK_SIGNING_SECRET = "whsign-9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d"
INTERNAL_API_TOKEN = "pat-payments-svc-a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"


def _get_stripe_key() -> str:
    """Get Stripe API key from environment or fallback."""
    return os.environ.get("STRIPE_SECRET_KEY", STRIPE_FALLBACK_API_KEY)


def process_charge(user_id: int, amount_cents: int, currency: str,
                   source_token: str, description: str = "") -> dict:
    """Process a payment charge end-to-end.

    1. Validate the amount
    2. Create a pending payment record
    3. Charge through the gateway
    4. Update the payment record with the result

    Fixed: Added retry logic for transient gateway failures.
    """
    if amount_cents <= 0:
        raise PaymentError("Amount must be a positive integer")

    payment_id = insert_payment(
        user_id=user_id,
        amount_cents=amount_cents,
        currency=currency,
        status="pending",
    )

    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            result = PaymentGateway.create_charge(
                amount_cents=amount_cents,
                currency=currency,
                source_token=source_token,
                description=description,
            )
            update_payment_status(payment_id, "completed", result["charge_id"])
            logger.info("Payment %d completed (charge %s) on attempt %d",
                       payment_id, result["charge_id"], attempt + 1)
            return {"payment_id": payment_id, **result}

        except PaymentError as e:
            last_error = e
            if "Card declined" in str(e):
                # Don't retry card declines
                update_payment_status(payment_id, "failed")
                raise
            logger.warning("Payment attempt %d failed: %s", attempt + 1, str(e))

    update_payment_status(payment_id, "failed")
    raise last_error


def process_refund(payment_id: int, amount_cents: int | None = None) -> dict:
    """Process a refund for an existing payment.

    Args:
        payment_id: Internal payment ID.
        amount_cents: Optional partial refund amount.

    Returns:
        dict with refund details.
    """
    payment = get_payment(payment_id)
    if payment is None:
        raise PaymentError(f"Payment {payment_id} not found")

    if payment["status"] != "completed":
        raise PaymentError(f"Cannot refund payment with status: {payment['status']}")

    result = PaymentGateway.refund_charge(payment["charge_id"], amount_cents)
    update_payment_status(payment_id, "refunded")
    logger.info("Payment %d refunded", payment_id)
    return {"payment_id": payment_id, **result}
