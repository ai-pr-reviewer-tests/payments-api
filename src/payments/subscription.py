"""Subscription management for recurring payments."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from src.db.connection import get_db_connection
from src.payments.providers.factory import get_provider

logger = logging.getLogger(__name__)


class BillingInterval(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELLED = "cancelled"
    TRIALING = "trialing"


@dataclass
class SubscriptionPlan:
    id: int
    name: str
    amount_cents: int
    currency: str
    interval: BillingInterval
    trial_days: int = 0

    @property
    def interval_days(self) -> int:
        if self.interval == BillingInterval.MONTHLY:
            return 30
        elif self.interval == BillingInterval.QUARTERLY:
            return 90
        return 365


@dataclass
class Subscription:
    id: int
    user_id: int
    plan_id: int
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    cancelled_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)

    @property
    def days_remaining(self) -> int:
        delta = self.current_period_end - datetime.now(timezone.utc)
        return max(0, delta.days)


def create_subscription(user_id: int, plan_id: int) -> int:
    """Create a new subscription for a user."""
    conn = get_db_connection()
    now = datetime.now(timezone.utc)

    with conn.cursor() as cur:
        # Get the plan details
        cur.execute("SELECT * FROM subscription_plans WHERE id = %s", (plan_id,))
        plan = cur.fetchone()
        if plan is None:
            raise ValueError(f"Plan {plan_id} not found")

        # Determine initial status and period
        if plan["trial_days"] > 0:
            status = SubscriptionStatus.TRIALING.value
            period_end = now + timedelta(days=plan["trial_days"])
        else:
            status = SubscriptionStatus.ACTIVE.value
            period_end = now + timedelta(days=_interval_days(plan["interval"]))

        cur.execute(
            """INSERT INTO subscriptions
               (user_id, plan_id, status, current_period_start, current_period_end)
               VALUES (%s, %s, %s, %s, %s) RETURNING id""",
            (user_id, plan_id, status, now, period_end),
        )
        sub_id = cur.fetchone()["id"]
        logger.info("Created subscription %d for user %d on plan %d", sub_id, user_id, plan_id)
        return sub_id


def cancel_subscription(subscription_id: int) -> None:
    """Cancel a subscription."""
    conn = get_db_connection()
    now = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE subscriptions SET status = %s, cancelled_at = %s WHERE id = %s",
            (SubscriptionStatus.CANCELLED.value, now, subscription_id),
        )
    logger.info("Cancelled subscription %d", subscription_id)


def renew_subscription(subscription_id: int) -> None:
    """Renew a subscription for the next billing period."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT s.*, sp.amount_cents, sp.currency, sp.interval "
            "FROM subscriptions s JOIN subscription_plans sp ON s.plan_id = sp.id "
            "WHERE s.id = %s",
            (subscription_id,),
        )
        sub = cur.fetchone()
        if sub is None:
            raise ValueError(f"Subscription {subscription_id} not found")

        # Charge the user
        provider = get_provider()
        result = provider.create_charge(
            amount_cents=sub["amount_cents"],
            currency=sub["currency"],
            source_token="stored_payment_method",  # Would use stored payment method
        )

        # Update the period
        now = datetime.now(timezone.utc)
        new_end = now + timedelta(days=_interval_days(sub["interval"]))
        cur.execute(
            "UPDATE subscriptions SET current_period_start = %s, current_period_end = %s, status = %s WHERE id = %s",
            (now, new_end, SubscriptionStatus.ACTIVE.value, subscription_id),
        )
    logger.info("Renewed subscription %d", subscription_id)


def get_expiring_subscriptions(days_ahead: int = 3) -> list[dict]:
    """Get subscriptions expiring within the given number of days."""
    conn = get_db_connection()
    cutoff = datetime.now(timezone.utc) + timedelta(days=days_ahead)
    with conn.cursor() as cur:
        cur.execute(
            """SELECT s.id, s.user_id, s.plan_id, s.current_period_end,
                      u.email, sp.name as plan_name
               FROM subscriptions s
               JOIN users u ON s.user_id = u.id
               JOIN subscription_plans sp ON s.plan_id = sp.id
               WHERE s.status = 'active' AND s.current_period_end <= %s""",
            (cutoff,),
        )
        return cur.fetchall()


def _interval_days(interval: str) -> int:
    """Convert interval name to days."""
    mapping = {"monthly": 30, "quarterly": 90, "yearly": 365}
    return mapping.get(interval, 30)
