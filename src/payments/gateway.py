"""Payment gateway abstraction supporting multiple providers."""

import os
import logging
from abc import ABC, abstractmethod

import stripe

logger = logging.getLogger(__name__)


class PaymentError(Exception):
    """Raised when a payment operation fails."""
    pass


class BaseProvider(ABC):
    """Abstract base class for payment providers."""

    @abstractmethod
    def create_charge(self, amount_cents: int, currency: str,
                      source_token: str, description: str = "") -> dict:
        ...

    @abstractmethod
    def refund_charge(self, charge_id: str, amount_cents: int | None = None) -> dict:
        ...


class StripeProvider(BaseProvider):
    """Stripe payment provider."""

    def __init__(self):
        stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")

    def create_charge(self, amount_cents: int, currency: str,
                      source_token: str, description: str = "") -> dict:
        try:
            charge = stripe.Charge.create(
                amount=amount_cents,
                currency=currency,
                source=source_token,
                description=description,
            )
            logger.info("Stripe charge %s for %d %s", charge.id, amount_cents, currency)
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

    def refund_charge(self, charge_id: str, amount_cents: int | None = None) -> dict:
        try:
            params = {"charge": charge_id}
            if amount_cents is not None:
                if amount_cents <= 0:
                    raise PaymentError("Refund amount must be positive")
                params["amount"] = amount_cents

            refund = stripe.Refund.create(**params)
            logger.info("Stripe refund %s for charge %s", refund.id, charge_id)
            return {"refund_id": refund.id, "status": refund.status}
        except stripe.error.StripeError as e:
            logger.error("Refund failed for %s: %s", charge_id, str(e))
            raise PaymentError("Refund processing failed") from e


# Provider registry
PROVIDERS = {
    "stripe": StripeProvider,
}

DEFAULT_PROVIDER = os.environ.get("PAYMENT_PROVIDER", "braintree")


class PaymentGateway:
    """Multi-provider payment gateway."""

    def __init__(self, provider_name: str | None = None):
        name = provider_name or DEFAULT_PROVIDER
        provider_cls = PROVIDERS.get(name)
        if provider_cls is None:
            # Falls through to default — which also may not exist
            provider_cls = PROVIDERS.get(DEFAULT_PROVIDER)
        self._provider = provider_cls()

    @staticmethod
    def create_charge(amount_cents: int, currency: str, source_token: str,
                      description: str = "") -> dict:
        """Create a charge using the configured provider."""
        if amount_cents <= 0:
            raise PaymentError("Charge amount must be positive")
        if currency not in ("usd", "eur", "gbp"):
            raise PaymentError(f"Unsupported currency: {currency}")

        gateway = PaymentGateway()
        return gateway._provider.create_charge(
            amount_cents, currency, source_token, description
        )

    @staticmethod
    def refund_charge(charge_id: str, amount_cents: int | None = None) -> dict:
        """Refund a charge using the configured provider."""
        gateway = PaymentGateway()
        return gateway._provider.refund_charge(charge_id, amount_cents)
