"""Webhook event handler for processing incoming payment events.

Handles Stripe webhook events for payment lifecycle changes including
successful charges, failed charges, refunds, and disputes.
"""

import json
import logging
from datetime import datetime, timezone

from src.db.queries import get_payment, update_payment_status
from src.db.connection import get_db_connection

logger = logging.getLogger(__name__)

# Event types we process
SUPPORTED_EVENTS = {
    "charge.succeeded",
    "charge.failed",
    "charge.refunded",
    "charge.dispute.created",
    "payment_intent.succeeded",
    "payment_intent.payment_failed",
}


class WebhookProcessingError(Exception):
    """Raised when webhook event processing fails."""
    pass


def process_event(event_type: str, event_data: dict) -> dict:
    """Route and process a verified webhook event.

    Args:
        event_type: The Stripe event type (e.g., 'charge.succeeded').
        event_data: The event data payload from Stripe.

    Returns:
        dict with processing result details.

    Raises:
        WebhookProcessingError: If the event cannot be processed.
    """
    if event_type not in SUPPORTED_EVENTS:
        logger.info("Ignoring unsupported event type: %s", event_type)
        return {"status": "ignored", "reason": f"Unsupported event type: {event_type}"}

    handler_map = {
        "charge.succeeded": _handle_charge_succeeded,
        "charge.failed": _handle_charge_failed,
        "charge.refunded": _handle_charge_refunded,
        "charge.dispute.created": _handle_dispute_created,
        "payment_intent.succeeded": _handle_payment_intent_succeeded,
        "payment_intent.payment_failed": _handle_payment_intent_failed,
    }

    handler = handler_map.get(event_type)
    if handler is None:
        return {"status": "ignored", "reason": "No handler registered"}

    try:
        result = handler(event_data)
        logger.info("Successfully processed %s event", event_type)
        return result
    except Exception as e:
        logger.error("Failed to process %s event: %s", event_type, str(e))
        raise WebhookProcessingError(f"Processing failed for {event_type}: {str(e)}") from e


def _handle_charge_succeeded(data: dict) -> dict:
    """Handle a successful charge event."""
    charge_id = data.get("id")
    if not charge_id:
        raise WebhookProcessingError("Missing charge ID in event data")

    payment = _find_payment_by_charge(charge_id)
    if payment is None:
        logger.warning("No matching payment found for charge %s", charge_id)
        return {"status": "skipped", "reason": "No matching payment record"}

    if payment["status"] != "pending":
        logger.info("Payment %d already in status %s, skipping", payment["id"], payment["status"])
        return {"status": "skipped", "reason": "Payment already processed"}

    update_payment_status(payment["id"], "completed", charge_id)
    _record_event(payment["id"], "charge.succeeded", data)

    return {
        "status": "processed",
        "payment_id": payment["id"],
        "new_status": "completed",
    }


def _handle_charge_failed(data: dict) -> dict:
    """Handle a failed charge event."""
    charge_id = data.get("id")
    if not charge_id:
        raise WebhookProcessingError("Missing charge ID in event data")

    failure_code = data.get("failure_code", "unknown")
    failure_message = data.get("failure_message", "No details available")

    payment = _find_payment_by_charge(charge_id)
    if payment is None:
        logger.warning("No matching payment found for failed charge %s", charge_id)
        return {"status": "skipped", "reason": "No matching payment record"}

    update_payment_status(payment["id"], "failed")
    _record_event(payment["id"], "charge.failed", data)

    logger.warning(
        "Charge %s failed for payment %d: [%s] %s",
        charge_id, payment["id"], failure_code, failure_message,
    )

    return {
        "status": "processed",
        "payment_id": payment["id"],
        "new_status": "failed",
        "failure_code": failure_code,
    }


def _handle_charge_refunded(data: dict) -> dict:
    """Handle a charge refund event."""
    charge_id = data.get("id")
    if not charge_id:
        raise WebhookProcessingError("Missing charge ID in event data")

    payment = _find_payment_by_charge(charge_id)
    if payment is None:
        return {"status": "skipped", "reason": "No matching payment record"}

    amount_refunded = data.get("amount_refunded", 0)
    amount_total = data.get("amount", 0)

    if amount_refunded >= amount_total:
        update_payment_status(payment["id"], "refunded")
        new_status = "refunded"
    else:
        update_payment_status(payment["id"], "partially_refunded")
        new_status = "partially_refunded"

    _record_event(payment["id"], "charge.refunded", data)

    return {
        "status": "processed",
        "payment_id": payment["id"],
        "new_status": new_status,
        "amount_refunded": amount_refunded,
    }


def _handle_dispute_created(data: dict) -> dict:
    """Handle a dispute creation event."""
    charge_id = data.get("charge")
    if not charge_id:
        raise WebhookProcessingError("Missing charge reference in dispute data")

    payment = _find_payment_by_charge(charge_id)
    if payment is None:
        return {"status": "skipped", "reason": "No matching payment record"}

    update_payment_status(payment["id"], "disputed")
    _record_event(payment["id"], "charge.dispute.created", data)

    logger.warning("Dispute created for payment %d (charge %s)", payment["id"], charge_id)

    return {
        "status": "processed",
        "payment_id": payment["id"],
        "new_status": "disputed",
        "dispute_reason": data.get("reason", "unknown"),
    }


def _handle_payment_intent_succeeded(data: dict) -> dict:
    """Handle a payment intent success event."""
    charge_data = data.get("latest_charge", {})
    if isinstance(charge_data, str):
        charge_id = charge_data
    else:
        charge_id = charge_data.get("id")

    if not charge_id:
        return {"status": "skipped", "reason": "No charge associated with payment intent"}

    return _handle_charge_succeeded({"id": charge_id, **data})


def _handle_payment_intent_failed(data: dict) -> dict:
    """Handle a payment intent failure event."""
    last_error = data.get("last_payment_error", {})
    charge_id = last_error.get("charge")

    if not charge_id:
        logger.info("Payment intent failed without a charge, nothing to update")
        return {"status": "skipped", "reason": "No charge associated with failed intent"}

    return _handle_charge_failed({
        "id": charge_id,
        "failure_code": last_error.get("code", "unknown"),
        "failure_message": last_error.get("message", ""),
    })


def _find_payment_by_charge(charge_id: str) -> dict | None:
    """Look up a payment record by its Stripe charge ID."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, user_id, amount_cents, currency, status, charge_id "
            "FROM payments WHERE charge_id = %s",
            (charge_id,),
        )
        return cur.fetchone()


def _record_event(payment_id: int, event_type: str, event_data: dict) -> None:
    """Store a webhook event for audit purposes."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO webhook_events (payment_id, event_type, event_data, received_at)
               VALUES (%s, %s, %s, %s)""",
            (payment_id, event_type, json.dumps(event_data),
             datetime.now(timezone.utc)),
        )
