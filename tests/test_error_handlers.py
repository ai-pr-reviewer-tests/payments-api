"""Tests for error handling and formatting."""

import pytest
from marshmallow import ValidationError

from src.payments.gateway import PaymentError
from src.errors.handlers import (
    classify_payment_error,
    format_payment_error,
    format_validation_error,
)


class TestClassifyPaymentError:
    def test_card_declined(self):
        assert classify_payment_error("Your card_declined at gateway") == "CARD_DECLINED"

    def test_insufficient_funds(self):
        assert classify_payment_error("insufficient_funds on account") == "INSUFFICIENT_FUNDS"

    def test_expired_card(self):
        assert classify_payment_error("expired_card detected") == "EXPIRED_CARD"

    def test_invalid_cvc(self):
        assert classify_payment_error("invalid_cvc provided") == "INVALID_CVC"

    def test_processing_error(self):
        assert classify_payment_error("processing_error occurred") == "PROCESSING_ERROR"

    def test_rate_limit(self):
        assert classify_payment_error("rate_limit reached") == "RATE_LIMIT_EXCEEDED"

    def test_unknown_error(self):
        assert classify_payment_error("something totally unknown") == "PAYMENT_FAILED"

    def test_case_insensitive(self):
        assert classify_payment_error("CARD_DECLINED") == "CARD_DECLINED"


class TestFormatPaymentError:
    def test_structure(self):
        error = PaymentError("Card declined: insufficient_funds")
        result = format_payment_error(error)

        assert "error" in result
        assert "code" in result["error"]
        assert "message" in result["error"]
        assert "details" in result["error"]
        assert "retry_allowed" in result["error"]

    def test_retry_allowed_for_processing_error(self):
        error = PaymentError("Temporary processing_error, try again")
        result = format_payment_error(error)
        assert result["error"]["retry_allowed"] is True

    def test_no_retry_for_card_declined(self):
        error = PaymentError("card_declined by issuer")
        result = format_payment_error(error)
        assert result["error"]["retry_allowed"] is False

    def test_user_friendly_message(self):
        error = PaymentError("expired_card error from processor")
        result = format_payment_error(error)
        assert "expired" in result["error"]["message"].lower()

    def test_details_contains_original_message(self):
        error = PaymentError("Card declined: insufficient_funds (request: req_123)")
        result = format_payment_error(error)
        assert "insufficient_funds" in result["error"]["details"]


class TestFormatValidationError:
    def test_structure(self):
        error = ValidationError({"amount_cents": ["Missing data for required field."]})
        result = format_validation_error(error)

        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert "fields" in result["error"]
        assert "amount_cents" in result["error"]["fields"]

    def test_multiple_field_errors(self):
        error = ValidationError({
            "amount_cents": ["Must be positive."],
            "currency": ["Invalid currency code."],
        })
        result = format_validation_error(error)
        assert len(result["error"]["fields"]) == 2
