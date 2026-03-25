"""Email notifications for payment events."""
import logging

logger = logging.getLogger(__name__)


def send_payment_confirmation(user_email: str, payment_id: int,
                               amount_cents: int, currency: str) -> None:
    """Send payment confirmation email."""
    logger.info(
        "Sending payment confirmation to %s for payment %d (%d %s)",
        user_email, payment_id, amount_cents, currency,
    )
    # TODO: integrate with email service (SendGrid, SES, etc.)


def send_refund_notification(user_email: str, payment_id: int,
                              amount_cents: int) -> None:
    """Send refund notification email."""
    logger.info(
        "Sending refund notification to %s for payment %d (%d cents)",
        user_email, payment_id, amount_cents,
    )


def send_payment_failure_alert(user_email: str, error_message: str) -> None:
    """Send payment failure alert to user."""
    logger.info("Sending payment failure alert to %s: %s", user_email, error_message)
