"""Tests for request validation."""
import pytest
from marshmallow import ValidationError
from src.api.validation import LoginSchema, ChargeSchema, RefundSchema


class TestLoginSchema:
    def test_valid_login(self):
        schema = LoginSchema()
        data = schema.load({"email": "user@test.com", "password": "secret"})
        assert data["email"] == "user@test.com"

    def test_missing_email(self):
        schema = LoginSchema()
        with pytest.raises(ValidationError):
            schema.load({"password": "secret"})

    def test_invalid_email(self):
        schema = LoginSchema()
        with pytest.raises(ValidationError):
            schema.load({"email": "not-email", "password": "secret"})

    def test_empty_password(self):
        schema = LoginSchema()
        with pytest.raises(ValidationError):
            schema.load({"email": "user@test.com", "password": ""})


class TestChargeSchema:
    def test_valid_charge(self):
        schema = ChargeSchema()
        data = schema.load({
            "amount_cents": 1000,
            "currency": "usd",
            "source_token": "tok_test",
        })
        assert data["amount_cents"] == 1000

    def test_zero_amount_rejected(self):
        schema = ChargeSchema()
        with pytest.raises(ValidationError):
            schema.load({
                "amount_cents": 0,
                "currency": "usd",
                "source_token": "tok_test",
            })

    def test_negative_amount_rejected(self):
        schema = ChargeSchema()
        with pytest.raises(ValidationError):
            schema.load({
                "amount_cents": -100,
                "currency": "usd",
                "source_token": "tok_test",
            })


class TestRefundSchema:
    def test_partial_refund(self):
        schema = RefundSchema()
        data = schema.load({"amount_cents": 500})
        assert data["amount_cents"] == 500

    def test_full_refund(self):
        schema = RefundSchema()
        data = schema.load({})
        assert data["amount_cents"] is None
