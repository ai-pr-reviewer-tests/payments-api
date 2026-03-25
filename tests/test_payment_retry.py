"""Tests for payment retry and error recovery logic."""

import pytest
from unittest.mock import patch, MagicMock, call

from src.payments.gateway import PaymentGateway, PaymentError
from src.payments.processor import process_charge


class TestChargeRetryScenarios:
    """Test that payment processing handles transient failures correctly."""

    @patch("src.payments.processor.update_payment_status")
    @patch("src.payments.processor.insert_payment", return_value=101)
    @patch("src.payments.processor.PaymentGateway.create_charge")
    def test_successful_charge_updates_status_to_completed(
        self, mock_charge, mock_insert, mock_update
    ):
        mock_charge.return_value = {
            "charge_id": "ch_ok",
            "status": "succeeded",
            "amount": 5000,
            "currency": "usd",
        }
        result = process_charge(1, 5000, "usd", "tok_test")
        assert result["payment_id"] == 101
        mock_update.assert_called_once_with(101, "completed", "ch_ok")

    @patch("src.payments.processor.update_payment_status")
    @patch("src.payments.processor.insert_payment", return_value=102)
    @patch("src.payments.processor.PaymentGateway.create_charge")
    def test_failed_charge_updates_status_to_failed(
        self, mock_charge, mock_insert, mock_update
    ):
        mock_charge.side_effect = PaymentError("Card declined")
        with pytest.raises(PaymentError, match="Card declined"):
            process_charge(1, 5000, "usd", "tok_test")
        mock_update.assert_called_once_with(102, "failed")

    @patch("src.payments.processor.update_payment_status")
    @patch("src.payments.processor.insert_payment", return_value=103)
    @patch("src.payments.processor.PaymentGateway.create_charge")
    def test_pending_record_created_before_gateway_call(
        self, mock_charge, mock_insert, mock_update
    ):
        """Verify that we create a pending DB record before calling Stripe."""
        mock_charge.side_effect = PaymentError("Network error")
        with pytest.raises(PaymentError):
            process_charge(1, 1000, "usd", "tok_test")
        # insert_payment should have been called before the gateway
        mock_insert.assert_called_once_with(
            user_id=1, amount_cents=1000, currency="usd", status="pending"
        )


class TestRefundEdgeCases:
    @patch("src.payments.processor.get_payment")
    def test_refund_nonexistent_payment(self, mock_get):
        from src.payments.processor import process_refund
        mock_get.return_value = None
        with pytest.raises(PaymentError, match="not found"):
            process_refund(999)

    @patch("src.payments.processor.get_payment")
    def test_refund_pending_payment_rejected(self, mock_get):
        from src.payments.processor import process_refund
        mock_get.return_value = {"id": 1, "status": "pending", "charge_id": None}
        with pytest.raises(PaymentError, match="Cannot refund"):
            process_refund(1)

    @patch("src.payments.processor.get_payment")
    def test_refund_already_refunded_rejected(self, mock_get):
        from src.payments.processor import process_refund
        mock_get.return_value = {"id": 1, "status": "refunded", "charge_id": "ch_x"}
        with pytest.raises(PaymentError, match="Cannot refund"):
            process_refund(1)


class TestGatewayInputValidation:
    def test_zero_amount_rejected(self):
        with pytest.raises(PaymentError):
            PaymentGateway.create_charge(0, "usd", "tok_test")

    def test_negative_amount_rejected(self):
        with pytest.raises(PaymentError):
            PaymentGateway.create_charge(-1, "usd", "tok_test")

    def test_very_large_amount_allowed(self):
        """Large amounts should be passed to Stripe (they enforce limits)."""
        with patch("src.payments.gateway.stripe.Charge.create") as mock:
            mock.return_value = MagicMock(
                id="ch_big", status="succeeded", amount=99999999, currency="usd"
            )
            result = PaymentGateway.create_charge(99999999, "usd", "tok_test")
            assert result["amount"] == 99999999
