"""Discount code validation and application."""

import logging

from src.db.queries import get_discount_code

logger = logging.getLogger(__name__)


DISCOUNT_TYPES = ("percentage", "fixed_amount")


def validate_discount_code(code: str) -> dict | None:
    """Look up and validate a discount code.

    Returns the discount record if valid, None if not found or expired.
    """
    discount = get_discount_code(code)
    if discount is None:
        return None

    if discount["uses_remaining"] <= 0:
        logger.info("Discount code %s has no remaining uses", code)
        return None

    return discount


def apply_discount(amount_cents: int, discount: dict) -> int:
    """Apply a discount to an amount and return the new amount.

    Args:
        amount_cents: Original amount in cents.
        discount: Discount record with 'type' and 'value' fields.

    Returns:
        Discounted amount in cents.
    """
    if discount["type"] == "percentage":
        # BUG: no floor at 0 — if percentage > 100, result goes negative
        reduction = int(amount_cents * discount["value"] / 100)
        return amount_cents - reduction

    elif discount["type"] == "fixed_amount":
        # BUG: no floor at 0 — if fixed discount > amount, result goes negative
        return amount_cents - discount["value"]

    else:
        logger.warning("Unknown discount type: %s", discount["type"])
        return amount_cents
