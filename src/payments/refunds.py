"""Refund processing with validation, partial refund support, and audit logging."""

import logging
from datetime import datetime, timezone
from decimal import Decimal

from src.db.connection import get_db_connection
from src.payments.gateway import PaymentGateway, PaymentError

logger = logging.getLogger(__name__)

REFUND_REASONS = (
    "customer_request",
    "duplicate_charge",
    "fraudulent",
    "product_not_received",
    "product_unacceptable",
    "other",
)

MAX_REFUND_AGE_DAYS = 180


def process_refund(payment_id: int, amount_cents: int | None = None,
                   reason: str = "customer_request", initiated_by: int | None = None) -> dict:
    """Process a full or partial refund for a completed payment.

    Args:
        payment_id: Internal payment ID to refund.
        amount_cents: Amount to refund in cents. None means full refund.
        reason: Reason code for the refund.
        initiated_by: User ID of the person initiating the refund.

    Returns:
        dict with refund details including refund_id, status, and amounts.

    Raises:
        PaymentError: If the refund cannot be processed.
    """
    if reason not in REFUND_REASONS:
        raise PaymentError(
            f"Invalid refund reason '{reason}'. "
            f"Must be one of: {', '.join(REFUND_REASONS)}"
        )

    payment = _get_payment_for_refund(payment_id)

    _validate_refund_eligibility(payment, amount_cents)

    refund_amount = amount_cents if amount_cents is not None else payment["amount_cents"]

    gateway_result = PaymentGateway.refund_charge(
        charge_id=payment["charge_id"],
        amount_cents=refund_amount,
    )

    is_partial = amount_cents is not None and amount_cents < payment["amount_cents"]
    new_status = "partially_refunded" if is_partial else "refunded"

    _update_payment_after_refund(payment_id, new_status, refund_amount)

    _record_refund_audit(
        payment_id=payment_id,
        refund_id=gateway_result["refund_id"],
        amount_cents=refund_amount,
        reason=reason,
        initiated_by=initiated_by,
    )

    logger.info(
        "Refund %s processed for payment %d: %d cents (%s)",
        gateway_result["refund_id"], payment_id, refund_amount, reason,
    )

    return {
        "payment_id": payment_id,
        "refund_id": gateway_result["refund_id"],
        "refund_status": gateway_result["status"],
        "refund_amount_cents": refund_amount,
        "is_partial": is_partial,
        "reason": reason,
        "payment_status": new_status,
    }


def get_refund_history(payment_id: int) -> list[dict]:
    """Retrieve all refund audit records for a payment."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, payment_id, refund_id, amount_cents, reason,
                      initiated_by, created_at
               FROM refund_audit_log
               WHERE payment_id = %s
               ORDER BY created_at DESC""",
            (payment_id,),
        )
        return cur.fetchall()


def get_total_refunded(payment_id: int) -> int:
    """Calculate the total amount already refunded for a payment."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COALESCE(SUM(amount_cents), 0) AS total FROM refund_audit_log WHERE payment_id = %s",
            (payment_id,),
        )
        row = cur.fetchone()
        return row["total"]


def _get_payment_for_refund(payment_id: int) -> dict:
    """Fetch and return the payment record, raising if not found."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, user_id, amount_cents, currency, status, charge_id, created_at
               FROM payments WHERE id = %s""",
            (payment_id,),
        )
        payment = cur.fetchone()

    if payment is None:
        raise PaymentError(f"Payment {payment_id} not found")

    return payment


def _validate_refund_eligibility(payment: dict, amount_cents: int | None) -> None:
    """Validate that the payment is eligible for the requested refund."""
    if payment["status"] not in ("completed", "partially_refunded"):
        raise PaymentError(
            f"Cannot refund payment with status '{payment['status']}'. "
            "Only completed or partially refunded payments are eligible."
        )

    if not payment.get("charge_id"):
        raise PaymentError(
            f"Payment {payment['id']} has no associated charge ID"
        )

    payment_age = datetime.now(timezone.utc) - payment["created_at"].replace(
        tzinfo=timezone.utc
    )
    if payment_age.days > MAX_REFUND_AGE_DAYS:
        raise PaymentError(
            f"Payment {payment['id']} is older than {MAX_REFUND_AGE_DAYS} days "
            "and is no longer eligible for refund"
        )

    if amount_cents is not None:
        if amount_cents <= 0:
            raise PaymentError("Refund amount must be a positive integer")

        already_refunded = get_total_refunded(payment["id"])
        remaining = payment["amount_cents"] - already_refunded

        if amount_cents > remaining:
            raise PaymentError(
                f"Refund amount ({amount_cents}) exceeds remaining refundable "
                f"amount ({remaining}) for payment {payment['id']}"
            )


def _update_payment_after_refund(payment_id: int, status: str,
                                 refund_amount_cents: int) -> None:
    """Update the payment record after a successful refund."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE payments
               SET status = %s, refunded_amount_cents = COALESCE(refunded_amount_cents, 0) + %s,
                   updated_at = NOW()
               WHERE id = %s""",
            (status, refund_amount_cents, payment_id),
        )


def _record_refund_audit(payment_id: int, refund_id: str, amount_cents: int,
                         reason: str, initiated_by: int | None) -> None:
    """Insert an audit log entry for the refund."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO refund_audit_log
               (payment_id, refund_id, amount_cents, reason, initiated_by, created_at)
               VALUES (%s, %s, %s, %s, %s, NOW())""",
            (payment_id, refund_id, amount_cents, reason, initiated_by),
        )
    logger.info(
        "Audit log entry created for refund %s on payment %d",
        refund_id, payment_id,
    )
