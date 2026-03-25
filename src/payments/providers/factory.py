"""Provider factory for creating payment provider instances."""
import os
import logging
from src.payments.providers.stripe_provider import StripeProvider
from src.payments.providers.braintree_provider import BraintreeProvider
from src.payments.providers.adyen_provider import AdyenProvider
from src.payments.providers.base import BasePaymentProvider

logger = logging.getLogger(__name__)

_PROVIDERS = {
    "stripe": StripeProvider,
    "braintree": BraintreeProvider,
    "adyen": AdyenProvider,
}

_instances: dict[str, BasePaymentProvider] = {}


def get_provider(name: str | None = None) -> BasePaymentProvider:
    """Get or create a payment provider instance."""
    if name is None:
        name = os.environ.get("PAYMENT_PROVIDER", "stripe")
    
    if name not in _instances:
        cls = _PROVIDERS.get(name)
        if cls is None:
            raise ValueError(f"Unknown payment provider: {name}")
        instance = cls()
        config = _load_provider_config(name)
        instance.initialize(config)
        _instances[name] = instance
    
    return _instances[name]


def _load_provider_config(name: str) -> dict:
    """Load provider-specific configuration from environment."""
    prefix = name.upper()
    return {
        key.lower().removeprefix(f"{prefix.lower()}_"): value
        for key, value in os.environ.items()
        if key.startswith(f"{prefix}_")
    }
