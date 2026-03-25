"""High-level payment processing logic."""

import logging

from src.db.queries import insert_payment, update_payment_status, get_payment
from src.payments.gateway import PaymentGateway, PaymentError

logger = logging.getLogger(__name__)


def process_charge(user_id: int, amount_cents: int, currency: str,
                   source_token: str, description: str = "") -> dict:
    """Process a payment charge end-to-end.

    1. Validate the amount
    2. Create a pending payment record
    3. Charge through the gateway
    4. Update the payment record with the result
    """
    if amount_cents <= 0:
        raise PaymentError("Amount must be a positive integer")

    payment_id = insert_payment(
        user_id=user_id,
        amount_cents=amount_cents,
        currency=currency,
        status="pending",
    )

    try:
        result = PaymentGateway.create_charge(
            amount_cents=amount_cents,
            currency=currency,
            source_token=source_token,
            description=description,
        )
        update_payment_status(payment_id, "completed", result["charge_id"])
        logger.info("Payment %d completed (charge %s)", payment_id, result["charge_id"])
        return {"payment_id": payment_id, **result}

    except PaymentError:
        update_payment_status(payment_id, "failed")
        raise


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
