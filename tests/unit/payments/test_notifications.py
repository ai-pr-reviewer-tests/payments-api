"""Tests for payment notifications."""
from src.payments.notifications.email import (
    send_payment_confirmation,
    send_refund_notification,
    send_payment_failure_alert,
)
from src.payments.notifications.slack import (
    notify_large_payment,
    notify_refund,
)


class TestEmailNotifications:
    def test_payment_confirmation(self):
        # Should not raise
        send_payment_confirmation("user@test.com", 1, 5000, "usd")

    def test_refund_notification(self):
        send_refund_notification("user@test.com", 1, 2500)

    def test_failure_alert(self):
        send_payment_failure_alert("user@test.com", "Card declined")


class TestSlackNotifications:
    def test_large_payment_alert(self):
        notify_large_payment(1, 150000, "usd")

    def test_small_payment_no_alert(self):
        notify_large_payment(1, 5000, "usd")

    def test_refund_notification(self):
        notify_refund(1, 5000)
