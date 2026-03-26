"""Stripe webhook event processing with deduplication and retry handling."""

import os
import logging
import time

import stripe

from src.db.connection import get_db_connection
from src.payments.gateway import PaymentError

logger = logging.getLogger(__name__)

STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
MAX_PROCESSING_RETRIES = 3
RETRY_BACKOFF_BASE = 0.5

_processed_events = set()


def verify_webhook_signature(payload: bytes, sig_header: str) -> dict:
    """Verify the Stripe webhook signature and return the parsed event.

    Args:
        payload: Raw request body bytes.
        sig_header: Value of the Stripe-Signature header.

    Returns:
        Parsed Stripe event as a dict.

    Raises:
        ValueError: If the signature is invalid or verification fails.
    """
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET,
        )
        return event
    except stripe.error.SignatureVerificationError as e:
        logger.warning("Webhook signature verification failed: %s", str(e))
        raise ValueError("Invalid webhook signature") from e
    except Exception as e:
        logger.error("Unexpected error verifying webhook: %s", str(e))
        raise ValueError("Webhook verification failed") from e


def handle_webhook_event(event: dict) -> dict:
    """Process a Stripe webhook event with deduplication.

    Checks whether the event has already been processed to prevent
    duplicate handling. Events are tracked by their Stripe event ID.

    Args:
        event: Parsed Stripe event dict.

    Returns:
        dict with processing result status.
    """
    event_id = event.get("id")
    event_type = event.get("type", "unknown")

    if not event_id:
        logger.warning("Received webhook event without an ID")
        return {"status": "rejected", "reason": "missing_event_id"}

    if event_id in _processed_events:
        logger.info("Skipping duplicate event %s (type: %s)", event_id, event_type)
        return {"status": "duplicate", "event_id": event_id}

    logger.info("Processing webhook event %s (type: %s)", event_id, event_type)

    result = _dispatch_event(event_id, event_type, event.get("data", {}))

    _processed_events.add(event_id)

    return result


def _dispatch_event(event_id: str, event_type: str, data: dict) -> dict:
    """Route the event to the appropriate handler based on type."""
    handlers = {
        "payment_intent.succeeded": _handle_payment_succeeded,
        "payment_intent.payment_failed": _handle_payment_failed,
        "charge.refunded": _handle_charge_refunded,
        "charge.dispute.created": _handle_dispute_created,
    }

    handler = handlers.get(event_type)
    if handler is None:
        logger.info("No handler for event type %s, acknowledging", event_type)
        return {"status": "acknowledged", "event_id": event_id, "event_type": event_type}

    return _execute_with_retry(handler, event_id, data)


def _execute_with_retry(handler, event_id: str, data: dict) -> dict:
    """Execute an event handler with retry logic for transient failures."""
    last_error = None

    for attempt in range(1, MAX_PROCESSING_RETRIES + 1):
        try:
            result = handler(data)
            result["event_id"] = event_id
            result["attempt"] = attempt
            return result
        except PaymentError as e:
            last_error = e
            logger.warning(
                "Payment error processing event %s (attempt %d/%d): %s",
                event_id, attempt, MAX_PROCESSING_RETRIES, str(e),
            )
            raise
        except Exception as e:
            last_error = e
            if attempt < MAX_PROCESSING_RETRIES:
                wait_time = RETRY_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning(
                    "Transient error processing event %s (attempt %d/%d): %s. "
                    "Retrying in %.1fs",
                    event_id, attempt, MAX_PROCESSING_RETRIES, str(e), wait_time,
                )
                time.sleep(wait_time)
            else:
                logger.error(
                    "Failed to process event %s after %d attempts: %s",
                    event_id, MAX_PROCESSING_RETRIES, str(e),
                )

    return {
        "status": "failed",
        "event_id": event_id,
        "error": str(last_error),
        "attempts": MAX_PROCESSING_RETRIES,
    }


def _handle_payment_succeeded(data: dict) -> dict:
    """Handle a successful payment intent."""
    obj = data.get("object", {})
    charge_id = obj.get("latest_charge")
    amount = obj.get("amount", 0)
    currency = obj.get("currency", "")

    if charge_id:
        _update_payment_by_charge(charge_id, "completed")

    logger.info(
        "Payment succeeded: charge=%s amount=%d currency=%s",
        charge_id, amount, currency,
    )
    return {"status": "processed", "event_type": "payment_intent.succeeded"}


def _handle_payment_failed(data: dict) -> dict:
    """Handle a failed payment intent."""
    obj = data.get("object", {})
    charge_id = obj.get("latest_charge")
    failure_message = obj.get("last_payment_error", {}).get("message", "Unknown")

    if charge_id:
        _update_payment_by_charge(charge_id, "failed")

    logger.warning("Payment failed: charge=%s reason=%s", charge_id, failure_message)
    return {"status": "processed", "event_type": "payment_intent.payment_failed"}


def _handle_charge_refunded(data: dict) -> dict:
    """Handle a charge refund event from Stripe."""
    obj = data.get("object", {})
    charge_id = obj.get("id")
    refunded = obj.get("refunded", False)
    amount_refunded = obj.get("amount_refunded", 0)

    if charge_id:
        new_status = "refunded" if refunded else "partially_refunded"
        _update_payment_by_charge(charge_id, new_status)

    logger.info(
        "Charge refunded: charge=%s fully_refunded=%s amount_refunded=%d",
        charge_id, refunded, amount_refunded,
    )
    return {"status": "processed", "event_type": "charge.refunded"}


def _handle_dispute_created(data: dict) -> dict:
    """Handle a new dispute on a charge."""
    obj = data.get("object", {})
    charge_id = obj.get("charge")
    dispute_amount = obj.get("amount", 0)
    reason = obj.get("reason", "unknown")

    if charge_id:
        _update_payment_by_charge(charge_id, "disputed")

    logger.warning(
        "Dispute created: charge=%s amount=%d reason=%s",
        charge_id, dispute_amount, reason,
    )
    return {"status": "processed", "event_type": "charge.dispute.created"}


def _update_payment_by_charge(charge_id: str, status: str) -> None:
    """Update payment status by looking up the Stripe charge ID."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE payments SET status = %s, updated_at = NOW() WHERE charge_id = %s",
            (status, charge_id),
        )
        if cur.rowcount == 0:
            logger.warning(
                "No payment found for charge %s when updating to status '%s'",
                charge_id, status,
            )
