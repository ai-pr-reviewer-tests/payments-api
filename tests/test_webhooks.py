"""Tests for webhook event processing and deduplication."""

import pytest
from unittest.mock import patch, MagicMock

from src.webhooks.handler import (
    handle_webhook_event,
    _dispatch_event,
    _processed_events,
    MAX_PROCESSING_RETRIES,
)
from src.payments.gateway import PaymentError


@pytest.fixture(autouse=True)
def clear_processed_events():
    """Clear the processed events set before each test."""
    _processed_events.clear()
    yield
    _processed_events.clear()


class TestWebhookDeduplication:
    def test_first_event_is_processed(self):
        event = {
            "id": "evt_test_001",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "latest_charge": "ch_abc",
                    "amount": 1000,
                    "currency": "usd",
                }
            },
        }
        with patch("src.webhooks.handler._update_payment_by_charge"):
            result = handle_webhook_event(event)
            assert result["status"] == "processed"
            assert result["event_id"] == "evt_test_001"

    def test_duplicate_event_is_skipped(self):
        event = {
            "id": "evt_test_002",
            "type": "payment_intent.succeeded",
            "data": {
                "object": {
                    "latest_charge": "ch_def",
                    "amount": 2000,
                    "currency": "usd",
                }
            },
        }
        with patch("src.webhooks.handler._update_payment_by_charge"):
            result1 = handle_webhook_event(event)
            assert result1["status"] == "processed"

            result2 = handle_webhook_event(event)
            assert result2["status"] == "duplicate"
            assert result2["event_id"] == "evt_test_002"

    def test_different_events_both_processed(self):
        event_a = {
            "id": "evt_test_003",
            "type": "payment_intent.succeeded",
            "data": {"object": {"latest_charge": "ch_aaa", "amount": 100, "currency": "usd"}},
        }
        event_b = {
            "id": "evt_test_004",
            "type": "payment_intent.succeeded",
            "data": {"object": {"latest_charge": "ch_bbb", "amount": 200, "currency": "usd"}},
        }
        with patch("src.webhooks.handler._update_payment_by_charge"):
            result_a = handle_webhook_event(event_a)
            result_b = handle_webhook_event(event_b)
            assert result_a["status"] == "processed"
            assert result_b["status"] == "processed"

    def test_event_without_id_rejected(self):
        event = {"type": "payment_intent.succeeded", "data": {}}
        result = handle_webhook_event(event)
        assert result["status"] == "rejected"
        assert result["reason"] == "missing_event_id"


class TestEventDispatching:
    @patch("src.webhooks.handler._update_payment_by_charge")
    def test_payment_succeeded(self, mock_update):
        result = _dispatch_event(
            "evt_100", "payment_intent.succeeded",
            {"object": {"latest_charge": "ch_xyz", "amount": 5000, "currency": "usd"}},
        )
        assert result["status"] == "processed"
        mock_update.assert_called_once_with("ch_xyz", "completed")

    @patch("src.webhooks.handler._update_payment_by_charge")
    def test_payment_failed(self, mock_update):
        result = _dispatch_event(
            "evt_101", "payment_intent.payment_failed",
            {"object": {"latest_charge": "ch_fail", "last_payment_error": {"message": "declined"}}},
        )
        assert result["status"] == "processed"
        mock_update.assert_called_once_with("ch_fail", "failed")

    @patch("src.webhooks.handler._update_payment_by_charge")
    def test_charge_refunded(self, mock_update):
        result = _dispatch_event(
            "evt_102", "charge.refunded",
            {"object": {"id": "ch_ref", "refunded": True, "amount_refunded": 3000}},
        )
        assert result["status"] == "processed"
        mock_update.assert_called_once_with("ch_ref", "refunded")

    @patch("src.webhooks.handler._update_payment_by_charge")
    def test_partial_refund(self, mock_update):
        result = _dispatch_event(
            "evt_103", "charge.refunded",
            {"object": {"id": "ch_part", "refunded": False, "amount_refunded": 500}},
        )
        assert result["status"] == "processed"
        mock_update.assert_called_once_with("ch_part", "partially_refunded")

    @patch("src.webhooks.handler._update_payment_by_charge")
    def test_dispute_created(self, mock_update):
        result = _dispatch_event(
            "evt_104", "charge.dispute.created",
            {"object": {"charge": "ch_disp", "amount": 10000, "reason": "fraudulent"}},
        )
        assert result["status"] == "processed"
        mock_update.assert_called_once_with("ch_disp", "disputed")

    def test_unknown_event_acknowledged(self):
        result = _dispatch_event("evt_105", "customer.subscription.created", {})
        assert result["status"] == "acknowledged"


class TestRetryLogic:
    @patch("src.webhooks.handler._update_payment_by_charge")
    def test_transient_error_retried(self, mock_update):
        mock_update.side_effect = [RuntimeError("DB timeout"), None]
        result = _dispatch_event(
            "evt_200", "payment_intent.succeeded",
            {"object": {"latest_charge": "ch_retry", "amount": 100, "currency": "usd"}},
        )
        assert result["status"] == "processed"
        assert result["attempt"] == 2

    @patch("src.webhooks.handler._update_payment_by_charge")
    def test_permanent_failure_after_retries(self, mock_update):
        mock_update.side_effect = RuntimeError("persistent failure")
        result = _dispatch_event(
            "evt_201", "payment_intent.succeeded",
            {"object": {"latest_charge": "ch_perm", "amount": 100, "currency": "usd"}},
        )
        assert result["status"] == "failed"
        assert result["attempts"] == MAX_PROCESSING_RETRIES

    @patch("src.webhooks.handler._update_payment_by_charge")
    def test_payment_error_not_retried(self, mock_update):
        mock_update.side_effect = PaymentError("bad payment")
        with pytest.raises(PaymentError):
            _dispatch_event(
                "evt_202", "payment_intent.succeeded",
                {"object": {"latest_charge": "ch_bad", "amount": 100, "currency": "usd"}},
            )
