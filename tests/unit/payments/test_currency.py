"""Tests for currency utilities."""

from src.utils.currency import (
    format_amount, cents_to_decimal, decimal_to_cents, is_supported_currency,
)


class TestFormatAmount:
    def test_usd(self):
        assert format_amount(1050, "usd") == "$10.50"

    def test_eur(self):
        result = format_amount(2000, "eur")
        assert "20.00" in result

    def test_jpy_no_decimals(self):
        result = format_amount(1000, "jpy")
        assert "1000" in result

    def test_unknown_currency(self):
        assert format_amount(500, "xyz") == "500 xyz"


class TestCentsToDecimal:
    def test_standard_conversion(self):
        assert cents_to_decimal(1050, "usd") == 10.50

    def test_jpy_conversion(self):
        assert cents_to_decimal(1000, "jpy") == 1000.0


class TestDecimalToCents:
    def test_standard_conversion(self):
        assert decimal_to_cents(10.50, "usd") == 1050

    def test_rounding(self):
        assert decimal_to_cents(10.999, "usd") == 1100


class TestIsSupportedCurrency:
    def test_supported(self):
        assert is_supported_currency("usd") is True
        assert is_supported_currency("eur") is True

    def test_unsupported(self):
        assert is_supported_currency("xyz") is False
