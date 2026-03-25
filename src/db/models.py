"""Lightweight data models (used for validation, not ORM)."""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    id: int
    email: str
    role: str
    created_at: datetime | None = None


@dataclass
class Payment:
    id: int
    user_id: int
    amount_cents: int
    currency: str
    status: str
    charge_id: str | None = None
    created_at: datetime | None = None

    @property
    def amount_dollars(self) -> float:
        return self.amount_cents / 100.0

    def is_refundable(self) -> bool:
        return self.status == "completed"
