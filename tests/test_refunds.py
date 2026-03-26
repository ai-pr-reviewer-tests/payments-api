"""Tests for refund processing."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from src.payments.refunds import (
    process_refund,
    get_refund_history,
    get_total_refunded,
    REFUND_REASONS,
    MAX_REFUND_AGE_DAYS,
)
from src.payments.gateway import PaymentError


def _make_payment(overrides=None):
    """Create a sample payment dict for testing."""
    payment = {
        "id": 42,
        "user_id": 1,
        "amount_cents": 5000,
        "currency": "usd",
        "status": "completed",
        "charge_id": "ch_test_abc123",
        "created_at": datetime.now(timezone.utc) - timedelta(days=1),
    }
    if overrides:
        payment.update(overrides)
    return payment


class TestProcessRefund:
    @patch("src.payments.refunds._record_refund_audit")
    @patch("src.payments.refunds._update_payment_after_refund")
    @patch("src.payments.refunds.PaymentGateway.refund_charge")
    @patch("src.payments.refunds.get_total_refunded", return_value=0)
    @patch("src.payments.refunds._get_payment_for_refund")
    def test_full_refund(self, mock_get, mock_total, mock_gateway,
                         mock_update, mock_audit):
        mock_get.return_value = _make_payment()
        mock_gateway.return_value = {"refund_id": "re_123", "status": "succeeded"}

        result = process_refund(42, reason="customer_request", initiated_by=1)

        assert result["payment_id"] == 42
        assert result["refund_id"] == "re_123"
        assert result["refund_amount_cents"] == 5000
        assert result["is_partial"] is False
        assert result["payment_status"] == "refunded"
        mock_gateway.assert_called_once_with(
            charge_id="ch_test_abc123", amount_cents=5000,
        )
        mock_update.assert_called_once_with(42, "refunded", 5000)
        mock_audit.assert_called_once()

    @patch("src.payments.refunds._record_refund_audit")
    @patch("src.payments.refunds._update_payment_after_refund")
    @patch("src.payments.refunds.PaymentGateway.refund_charge")
    @patch("src.payments.refunds.get_total_refunded", return_value=0)
    @patch("src.payments.refunds._get_payment_for_refund")
    def test_partial_refund(self, mock_get, mock_total, mock_gateway,
                            mock_update, mock_audit):
        mock_get.return_value = _make_payment()
        mock_gateway.return_value = {"refund_id": "re_456", "status": "succeeded"}

        result = process_refund(42, amount_cents=2000, reason="duplicate_charge")

        assert result["refund_amount_cents"] == 2000
        assert result["is_partial"] is True
        assert result["payment_status"] == "partially_refunded"
        mock_gateway.assert_called_once_with(
            charge_id="ch_test_abc123", amount_cents=2000,
        )

    @patch("src.payments.refunds._get_payment_for_refund")
    def test_invalid_reason_rejected(self, mock_get):
        mock_get.return_value = _make_payment()

        with pytest.raises(PaymentError, match="Invalid refund reason"):
            process_refund(42, reason="because_i_said_so")

    @patch("src.payments.refunds._get_payment_for_refund")
    def test_pending_payment_cannot_be_refunded(self, mock_get):
        mock_get.return_value = _make_payment({"status": "pending"})

        with pytest.raises(PaymentError, match="Cannot refund payment"):
            process_refund(42)

    @patch("src.payments.refunds._get_payment_for_refund")
    def test_failed_payment_cannot_be_refunded(self, mock_get):
        mock_get.return_value = _make_payment({"status": "failed"})

        with pytest.raises(PaymentError, match="Cannot refund payment"):
            process_refund(42)

    @patch("src.payments.refunds.get_total_refunded", return_value=3000)
    @patch("src.payments.refunds._get_payment_for_refund")
    def test_refund_exceeding_remaining_amount(self, mock_get, mock_total):
        mock_get.return_value = _make_payment({"status": "partially_refunded"})

        with pytest.raises(PaymentError, match="exceeds remaining"):
            process_refund(42, amount_cents=3000)

    @patch("src.payments.refunds.get_total_refunded", return_value=0)
    @patch("src.payments.refunds._get_payment_for_refund")
    def test_expired_payment_cannot_be_refunded(self, mock_get, mock_total):
        old_date = datetime.now(timezone.utc) - timedelta(days=MAX_REFUND_AGE_DAYS + 1)
        mock_get.return_value = _make_payment({"created_at": old_date})

        with pytest.raises(PaymentError, match="no longer eligible"):
            process_refund(42)

    @patch("src.payments.refunds._get_payment_for_refund")
    def test_missing_charge_id_rejected(self, mock_get):
        mock_get.return_value = _make_payment({"charge_id": None})

        with pytest.raises(PaymentError, match="no associated charge ID"):
            process_refund(42)

    def test_payment_not_found(self):
        with patch("src.payments.refunds._get_payment_for_refund") as mock_get:
            mock_get.side_effect = PaymentError("Payment 999 not found")
            with pytest.raises(PaymentError, match="not found"):
                process_refund(999)


class TestRefundReasons:
    def test_all_reasons_are_strings(self):
        for reason in REFUND_REASONS:
            assert isinstance(reason, str)

    def test_common_reasons_included(self):
        assert "customer_request" in REFUND_REASONS
        assert "fraudulent" in REFUND_REASONS
        assert "duplicate_charge" in REFUND_REASONS


class TestRefundHistory:
    @patch("src.payments.refunds.get_db_connection")
    def test_get_refund_history(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )
        mock_cursor.fetchall.return_value = [
            {"id": 1, "refund_id": "re_abc", "amount_cents": 2000},
            {"id": 2, "refund_id": "re_def", "amount_cents": 1000},
        ]

        result = get_refund_history(42)
        assert len(result) == 2

    @patch("src.payments.refunds.get_db_connection")
    def test_get_total_refunded(self, mock_conn):
        mock_cursor = MagicMock()
        mock_conn.return_value.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(
            return_value=False
        )
        mock_cursor.fetchone.return_value = {"total": 3500}

        total = get_total_refunded(42)
        assert total == 3500
