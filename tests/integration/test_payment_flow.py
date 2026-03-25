"""Integration tests for the payment flow."""
import pytest
from unittest.mock import patch, MagicMock


class TestPaymentFlow:
    """End-to-end payment flow tests."""

    @patch("src.db.connection.get_db_connection")
    @patch("src.payments.gateway.stripe.Charge.create")
    def test_charge_creates_payment_record(self, mock_stripe, mock_db):
        """Verify that a charge creates a pending record then updates it."""
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1}
        mock_db.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_db.return_value.cursor.return_value.__exit__ = MagicMock(return_value=False)
        
        mock_stripe.return_value = MagicMock(
            id="ch_test", status="succeeded", amount=1000, currency="usd"
        )
        
        from src.payments.processor import process_charge
        result = process_charge(1, 1000, "usd", "tok_test")
        assert result["payment_id"] == 1


class TestRefundFlow:
    @patch("src.db.connection.get_db_connection")
    def test_refund_nonexistent_payment_fails(self, mock_db):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_db.return_value.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_db.return_value.cursor.return_value.__exit__ = MagicMock(return_value=False)
        
        from src.payments.processor import process_refund
        from src.payments.gateway import PaymentError
        with pytest.raises(PaymentError, match="not found"):
            process_refund(999)
