"""Base payment provider interface."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class ChargeStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class ChargeResult:
    provider_charge_id: str
    status: ChargeStatus
    amount_cents: int
    currency: str
    error_message: str | None = None
    metadata: dict | None = None


@dataclass
class RefundResult:
    provider_refund_id: str
    status: str
    amount_cents: int


class BasePaymentProvider(ABC):
    """Abstract base class for payment providers."""

    @abstractmethod
    def initialize(self, config: dict) -> None:
        """Initialize the provider with configuration."""
        ...

    @abstractmethod
    def create_charge(self, amount_cents: int, currency: str,
                      source_token: str, **kwargs) -> ChargeResult:
        """Create a charge."""
        ...

    @abstractmethod
    def refund_charge(self, charge_id: str,
                      amount_cents: int | None = None) -> RefundResult:
        """Refund a charge."""
        ...

    @abstractmethod
    def get_charge_status(self, charge_id: str) -> ChargeStatus:
        """Get the current status of a charge."""
        ...

    @abstractmethod
    def validate_webhook(self, payload: bytes, signature: str) -> bool:
        """Validate a webhook signature."""
        ...

    def supports_currency(self, currency: str) -> bool:
        """Check if the provider supports a currency."""
        return currency in self.supported_currencies()

    @abstractmethod
    def supported_currencies(self) -> list[str]:
        """Return list of supported currency codes."""
        ...
