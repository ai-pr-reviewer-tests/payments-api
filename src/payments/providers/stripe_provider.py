"""Stripe payment provider implementation."""
import logging
import stripe
from src.payments.providers.base import (
    BasePaymentProvider, ChargeResult, RefundResult, ChargeStatus,
)

logger = logging.getLogger(__name__)


class StripeProvider(BasePaymentProvider):
    """Stripe payment provider."""

    def __init__(self):
        self._api_key = None
        self._webhook_secret = None

    def initialize(self, config: dict) -> None:
        self._api_key = config.get("api_key", "")
        self._webhook_secret = config.get("webhook_secret", "")
        stripe.api_key = self._api_key

    def create_charge(self, amount_cents: int, currency: str,
                      source_token: str, **kwargs) -> ChargeResult:
        try:
            charge = stripe.Charge.create(
                amount=amount_cents,
                currency=currency,
                source=source_token,
                description=kwargs.get("description", ""),
                metadata=kwargs.get("metadata", {}),
            )
            return ChargeResult(
                provider_charge_id=charge.id,
                status=ChargeStatus.SUCCEEDED if charge.status == "succeeded"
                       else ChargeStatus.PENDING,
                amount_cents=charge.amount,
                currency=charge.currency,
            )
        except stripe.error.CardError as e:
            return ChargeResult(
                provider_charge_id="",
                status=ChargeStatus.FAILED,
                amount_cents=amount_cents,
                currency=currency,
                error_message=e.user_message,
            )

    def refund_charge(self, charge_id: str,
                      amount_cents: int | None = None) -> RefundResult:
        params = {"charge": charge_id}
        if amount_cents:
            params["amount"] = amount_cents
        refund = stripe.Refund.create(**params)
        return RefundResult(
            provider_refund_id=refund.id,
            status=refund.status,
            amount_cents=refund.amount,
        )

    def get_charge_status(self, charge_id: str) -> ChargeStatus:
        charge = stripe.Charge.retrieve(charge_id)
        status_map = {
            "succeeded": ChargeStatus.SUCCEEDED,
            "pending": ChargeStatus.PENDING,
            "failed": ChargeStatus.FAILED,
        }
        return status_map.get(charge.status, ChargeStatus.PENDING)

    def validate_webhook(self, payload: bytes, signature: str) -> bool:
        try:
            stripe.Webhook.construct_event(
                payload, signature, self._webhook_secret
            )
            return True
        except (ValueError, stripe.error.SignatureVerificationError):
            return False

    def supported_currencies(self) -> list[str]:
        return ["usd", "eur", "gbp", "cad", "aud", "jpy"]
