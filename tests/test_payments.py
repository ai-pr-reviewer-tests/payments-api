"""Tests for payment processing."""

import pytest
from unittest.mock import patch, MagicMock

from src.payments.gateway import PaymentGateway, PaymentError


class TestPaymentGateway:
    def test_reject_non_positive_amount(self):
        with pytest.raises(PaymentError, match="positive"):
            PaymentGateway.create_charge(0, "usd", "tok_test")

    def test_reject_negative_amount(self):
        with pytest.raises(PaymentError, match="positive"):
            PaymentGateway.create_charge(-100, "usd", "tok_test")

    def test_reject_unsupported_currency(self):
        with pytest.raises(PaymentError, match="Unsupported currency"):
            PaymentGateway.create_charge(1000, "jpy", "tok_test")

    @patch("src.payments.gateway.stripe.Charge.create")
    def test_successful_charge(self, mock_charge):
        mock_charge.return_value = MagicMock(
            id="ch_test123",
            status="succeeded",
            amount=1000,
            currency="usd",
        )
        result = PaymentGateway.create_charge(1000, "usd", "tok_test")
        assert result["charge_id"] == "ch_test123"
        assert result["status"] == "succeeded"

    def test_refund_rejects_non_positive(self):
        with pytest.raises(PaymentError, match="positive"):
            PaymentGateway.refund_charge("ch_test", amount_cents=-50)


class TestPaymentValidation:
    def test_charge_schema(self):
        from src.api.validation import ChargeSchema
        schema = ChargeSchema()
        result = schema.load({
            "amount_cents": 500,
            "currency": "usd",
            "source_token": "tok_test",
        })
        assert result["amount_cents"] == 500
        assert result["description"] == ""

    def test_charge_schema_rejects_bad_currency(self):
        from marshmallow import ValidationError
        from src.api.validation import ChargeSchema
        schema = ChargeSchema()
        with pytest.raises(ValidationError):
            schema.load({
                "amount_cents": 500,
                "currency": "xyz",
                "source_token": "tok_test",
            })
