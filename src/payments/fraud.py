"""Fraud detection and prevention."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from src.db.connection import get_db_connection
from src.cache.redis_client import get_redis

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FraudCheck:
    """Result of a fraud check."""
    risk_level: RiskLevel
    score: float
    reasons: list[str]
    should_block: bool

    @property
    def is_safe(self) -> bool:
        return self.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)


# Thresholds for fraud detection
VELOCITY_WINDOW_MINUTES = 60
MAX_TRANSACTIONS_PER_WINDOW = 20
HIGH_VALUE_THRESHOLD_CENTS = 500000  # $5,000
SUSPICIOUS_AMOUNT_THRESHOLD_CENTS = 1000000  # $10,000


def check_transaction(user_id: int, amount_cents: int,
                      currency: str, ip_address: str | None = None) -> FraudCheck:
    """Run fraud checks on a transaction.

    Args:
        user_id: The user initiating the transaction.
        amount_cents: Transaction amount in cents.
        currency: Currency code.
        ip_address: Client IP address.

    Returns:
        FraudCheck with risk assessment.
    """
    reasons = []
    score = 0.0

    # Check 1: Velocity — too many transactions in a short period
    velocity_score = _check_velocity(user_id)
    score += velocity_score
    if velocity_score > 0.3:
        reasons.append(f"High transaction velocity (score: {velocity_score:.2f})")

    # Check 2: Amount — unusually large transaction
    amount_score = _check_amount(amount_cents)
    score += amount_score
    if amount_score > 0.2:
        reasons.append(f"Large transaction amount: {amount_cents} cents")

    # Check 3: IP reputation (simplified)
    if ip_address:
        ip_score = _check_ip(ip_address)
        score += ip_score
        if ip_score > 0.1:
            reasons.append(f"Suspicious IP address: {ip_address}")

    # Check 4: Account age
    age_score = _check_account_age(user_id)
    score += age_score
    if age_score > 0.2:
        reasons.append("New account with limited history")

    # Determine risk level
    if score >= 0.8:
        risk_level = RiskLevel.CRITICAL
    elif score >= 0.5:
        risk_level = RiskLevel.HIGH
    elif score >= 0.3:
        risk_level = RiskLevel.MEDIUM
    else:
        risk_level = RiskLevel.LOW

    should_block = risk_level == RiskLevel.CRITICAL

    check = FraudCheck(
        risk_level=risk_level,
        score=score,
        reasons=reasons,
        should_block=should_block,
    )

    if check.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        logger.warning(
            "Fraud check flagged user %d: level=%s score=%.2f reasons=%s",
            user_id, check.risk_level.value, check.score, check.reasons,
        )

    return check


def _check_velocity(user_id: int) -> float:
    """Check transaction velocity for a user."""
    r = get_redis()
    key = f"fraud:velocity:{user_id}"
    count = r.get(key)
    if count is None:
        return 0.0
    count = int(count)
    if count > MAX_TRANSACTIONS_PER_WINDOW:
        return 0.5
    elif count > MAX_TRANSACTIONS_PER_WINDOW / 2:
        return 0.2
    return 0.0


def _check_amount(amount_cents: int) -> float:
    """Score based on transaction amount."""
    if amount_cents >= SUSPICIOUS_AMOUNT_THRESHOLD_CENTS:
        return 0.5
    elif amount_cents >= HIGH_VALUE_THRESHOLD_CENTS:
        return 0.2
    return 0.0


def _check_ip(ip_address: str) -> float:
    """Check IP address reputation (simplified)."""
    # In production, this would check against an IP reputation service
    r = get_redis()
    key = f"fraud:blocked_ip:{ip_address}"
    if r.exists(key):
        return 0.5
    return 0.0


def _check_account_age(user_id: int) -> float:
    """Score based on account age."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT created_at FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if user is None:
            return 0.3

        age = datetime.now(timezone.utc) - user["created_at"]
        if age < timedelta(hours=24):
            return 0.3
        elif age < timedelta(days=7):
            return 0.1
        return 0.0


def record_transaction(user_id: int) -> None:
    """Record a transaction for velocity tracking."""
    r = get_redis()
    key = f"fraud:velocity:{user_id}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, VELOCITY_WINDOW_MINUTES * 60)
    pipe.execute()
