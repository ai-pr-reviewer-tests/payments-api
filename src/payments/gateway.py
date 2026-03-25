"""Payment gateway abstraction over Stripe."""

import os
import logging

import stripe

logger = logging.getLogger(__name__)

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")


class PaymentGateway:
    """Thin wrapper around the Stripe API for charge and refund operations."""

    @staticmethod
    def create_charge(amount_cents: int, currency: str, source_token: str,
                      description: str = "") -> dict:
        """Create a charge through Stripe.

        Args:
            amount_cents: Amount in the smallest currency unit (e.g. cents).
            currency: Three-letter ISO currency code.
            source_token: Payment source token from the client.
            description: Optional charge description.

        Returns:
            dict with charge id, status, and amount.

        Raises:
            PaymentError: If the charge fails.
        """
        if amount_cents <= 0:
            raise PaymentError("Charge amount must be positive")

        if currency not in ("usd", "eur", "gbp"):
            raise PaymentError(f"Unsupported currency: {currency}")

        try:
            charge = stripe.Charge.create(
                amount=amount_cents,
                currency=currency,
                source=source_token,
                description=description,
            )
            logger.info("Charge %s created for %d %s", charge.id, amount_cents, currency)
            return {
                "charge_id": charge.id,
                "status": charge.status,
                "amount": charge.amount,
                "currency": charge.currency,
            }
        except stripe.error.CardError as e:
            logger.warning("Card declined: %s", e.user_message)
            raise PaymentError(f"Card declined: {e.user_message}") from e
        except stripe.error.StripeError as e:
            logger.error("Stripe error: %s", str(e))
            raise PaymentError("Payment processing failed") from e

    @staticmethod
    def refund_charge(charge_id: str, amount_cents: int | None = None) -> dict:
        """Refund a charge, fully or partially.

        Args:
            charge_id: The Stripe charge ID.
            amount_cents: If provided, refund this amount; otherwise full refund.

        Returns:
            dict with refund id and status.
        """
        try:
            params = {"charge": charge_id}
            if amount_cents is not None:
                if amount_cents <= 0:
                    raise PaymentError("Refund amount must be positive")
                params["amount"] = amount_cents

            refund = stripe.Refund.create(**params)
            logger.info("Refund %s created for charge %s", refund.id, charge_id)
            return {"refund_id": refund.id, "status": refund.status}
        except stripe.error.StripeError as e:
            logger.error("Refund failed for %s: %s", charge_id, str(e))
            raise PaymentError("Refund processing failed") from e


class PaymentError(Exception):
    """Raised when a payment operation fails."""
    pass
