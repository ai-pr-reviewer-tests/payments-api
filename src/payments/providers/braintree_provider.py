"""Braintree payment provider implementation."""
import logging
from src.payments.providers.base import (
    BasePaymentProvider, ChargeResult, RefundResult, ChargeStatus,
)

logger = logging.getLogger(__name__)


class BraintreeProvider(BasePaymentProvider):
    """Braintree payment provider (placeholder)."""

    def __init__(self):
        self._merchant_id = None
        self._public_key = None
        self._private_key = None

    def initialize(self, config: dict) -> None:
        self._merchant_id = config.get("merchant_id", "")
        self._public_key = config.get("public_key", "")
        self._private_key = config.get("private_key", "")

    def create_charge(self, amount_cents: int, currency: str,
                      source_token: str, **kwargs) -> ChargeResult:
        logger.info("Braintree charge: %d %s", amount_cents, currency)
        # Placeholder — real implementation would use braintree SDK
        raise NotImplementedError("Braintree provider not yet implemented")

    def refund_charge(self, charge_id: str,
                      amount_cents: int | None = None) -> RefundResult:
        raise NotImplementedError("Braintree provider not yet implemented")

    def get_charge_status(self, charge_id: str) -> ChargeStatus:
        raise NotImplementedError("Braintree provider not yet implemented")

    def validate_webhook(self, payload: bytes, signature: str) -> bool:
        raise NotImplementedError("Braintree provider not yet implemented")

    def supported_currencies(self) -> list[str]:
        return ["usd", "eur", "gbp", "cad", "aud"]
