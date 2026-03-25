"""Slack notifications for payment events."""
import logging
import os

logger = logging.getLogger(__name__)

SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")


def notify_large_payment(payment_id: int, amount_cents: int,
                          currency: str) -> None:
    """Notify Slack channel about large payments for fraud review."""
    if amount_cents < 100000:  # $1000 threshold
        return
    logger.info(
        "Large payment alert: payment %d for %d %s",
        payment_id, amount_cents, currency,
    )
    # TODO: POST to Slack webhook


def notify_refund(payment_id: int, amount_cents: int) -> None:
    """Notify Slack about refunds."""
    logger.info("Refund notification: payment %d for %d cents", payment_id, amount_cents)


def notify_provider_error(provider: str, error: str) -> None:
    """Alert about payment provider errors."""
    logger.error("Provider %s error: %s", provider, error)
