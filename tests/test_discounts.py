"""Tests for discount code logic."""

import pytest
from unittest.mock import patch

from src.payments.discounts import validate_discount_code, apply_discount


class TestValidateDiscountCode:
    @patch("src.payments.discounts.get_discount_code")
    def test_valid_code(self, mock_get):
        mock_get.return_value = {
            "id": 1, "code": "SAVE10", "type": "percentage",
            "value": 10, "uses_remaining": 5,
        }
        result = validate_discount_code("SAVE10")
        assert result is not None
        assert result["code"] == "SAVE10"

    @patch("src.payments.discounts.get_discount_code")
    def test_unknown_code_returns_none(self, mock_get):
        mock_get.return_value = None
        assert validate_discount_code("FAKE") is None

    @patch("src.payments.discounts.get_discount_code")
    def test_exhausted_code_returns_none(self, mock_get):
        mock_get.return_value = {
            "id": 2, "code": "USED", "type": "percentage",
            "value": 10, "uses_remaining": 0,
        }
        assert validate_discount_code("USED") is None


class TestApplyDiscount:
    def test_percentage_discount(self):
        discount = {"type": "percentage", "value": 20}
        assert apply_discount(10000, discount) == 8000  # $100 - 20% = $80

    def test_fixed_amount_discount(self):
        discount = {"type": "fixed_amount", "value": 500}
        assert apply_discount(2000, discount) == 1500  # $20 - $5 = $15

    def test_unknown_type_returns_original(self):
        discount = {"type": "bogus", "value": 50}
        assert apply_discount(1000, discount) == 1000

    def test_small_percentage_discount(self):
        discount = {"type": "percentage", "value": 5}
        assert apply_discount(1000, discount) == 950  # $10 - 5% = $9.50
