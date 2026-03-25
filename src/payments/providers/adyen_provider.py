"""Adyen payment provider implementation."""
import logging
from src.payments.providers.base import (
    BasePaymentProvider, ChargeResult, RefundResult, ChargeStatus,
)

logger = logging.getLogger(__name__)


class AdyenProvider(BasePaymentProvider):
    """Adyen payment provider (placeholder)."""

    def __init__(self):
        self._api_key = None
        self._merchant_account = None

    def initialize(self, config: dict) -> None:
        self._api_key = config.get("api_key", "")
        self._merchant_account = config.get("merchant_account", "")

    def create_charge(self, amount_cents: int, currency: str,
                      source_token: str, **kwargs) -> ChargeResult:
        logger.info("Adyen charge: %d %s", amount_cents, currency)
        raise NotImplementedError("Adyen provider not yet implemented")

    def refund_charge(self, charge_id: str,
                      amount_cents: int | None = None) -> RefundResult:
        raise NotImplementedError("Adyen provider not yet implemented")

    def get_charge_status(self, charge_id: str) -> ChargeStatus:
        raise NotImplementedError("Adyen provider not yet implemented")

    def validate_webhook(self, payload: bytes, signature: str) -> bool:
        raise NotImplementedError("Adyen provider not yet implemented")

    def supported_currencies(self) -> list[str]:
        return ["usd", "eur", "gbp"]
