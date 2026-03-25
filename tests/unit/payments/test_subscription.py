"""Tests for subscription management."""

import pytest
from datetime import datetime, timezone
from src.payments.subscription import (
    SubscriptionPlan, Subscription, SubscriptionStatus, BillingInterval,
)


class TestSubscriptionPlan:
    def test_monthly_interval_days(self):
        plan = SubscriptionPlan(
            id=1, name="Basic", amount_cents=999,
            currency="usd", interval=BillingInterval.MONTHLY,
        )
        assert plan.interval_days == 30

    def test_yearly_interval_days(self):
        plan = SubscriptionPlan(
            id=2, name="Pro", amount_cents=9999,
            currency="usd", interval=BillingInterval.YEARLY,
        )
        assert plan.interval_days == 365

    def test_quarterly_interval_days(self):
        plan = SubscriptionPlan(
            id=3, name="Team", amount_cents=4999,
            currency="usd", interval=BillingInterval.QUARTERLY,
        )
        assert plan.interval_days == 90


class TestSubscription:
    def test_active_subscription(self):
        now = datetime.now(timezone.utc)
        sub = Subscription(
            id=1, user_id=1, plan_id=1,
            status=SubscriptionStatus.ACTIVE,
            current_period_start=now,
            current_period_end=now,
        )
        assert sub.is_active is True

    def test_cancelled_subscription(self):
        now = datetime.now(timezone.utc)
        sub = Subscription(
            id=1, user_id=1, plan_id=1,
            status=SubscriptionStatus.CANCELLED,
            current_period_start=now,
            current_period_end=now,
        )
        assert sub.is_active is False

    def test_trialing_is_active(self):
        now = datetime.now(timezone.utc)
        sub = Subscription(
            id=1, user_id=1, plan_id=1,
            status=SubscriptionStatus.TRIALING,
            current_period_start=now,
            current_period_end=now,
        )
        assert sub.is_active is True
