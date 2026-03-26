"""Tests for currency conversion logic."""

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

from src.payments.currency import (
    get_exchange_rate,
    convert_amount,
    SUPPORTED_CURRENCIES,
    BASE_CURRENCY,
)


@pytest.fixture(autouse=True)
def mock_rates():
    """Set up test exchange rates."""
    test_rates = {
        "usd_eur": Decimal("0.92"),
        "usd_gbp": Decimal("0.79"),
        "usd_cad": Decimal("1.36"),
        "usd_aud": Decimal("1.53"),
        "usd_jpy": Decimal("149.50"),
        "usd_chf": Decimal("0.88"),
        "usd_sek": Decimal("10.45"),
        "usd_nok": Decimal("10.72"),
        "usd_dkk": Decimal("6.87"),
    }
    with patch("src.payments.currency._rates", test_rates):
        yield test_rates


class TestGetExchangeRate:
    def test_same_currency_returns_one(self):
        rate = get_exchange_rate("usd", "usd")
        assert rate == Decimal("1")

    def test_direct_rate(self):
        rate = get_exchange_rate("usd", "eur")
        assert rate == Decimal("0.92")

    def test_inverse_rate(self):
        rate = get_exchange_rate("eur", "usd")
        expected = Decimal("1") / Decimal("0.92")
        assert abs(rate - expected) < Decimal("0.0001")

    def test_cross_rate_through_base(self):
        rate = get_exchange_rate("eur", "gbp")
        eur_to_usd = Decimal("1") / Decimal("0.92")
        usd_to_gbp = Decimal("0.79")
        expected = eur_to_usd * usd_to_gbp
        assert abs(rate - expected) < Decimal("0.0001")

    def test_unsupported_source_currency(self):
        with pytest.raises(ValueError, match="Unsupported source currency"):
            get_exchange_rate("xyz", "usd")

    def test_unsupported_target_currency(self):
        with pytest.raises(ValueError, match="Unsupported target currency"):
            get_exchange_rate("usd", "xyz")

    def test_case_insensitive(self):
        rate = get_exchange_rate("USD", "EUR")
        assert rate == Decimal("0.92")


class TestConvertAmount:
    def test_same_currency_no_conversion(self):
        result = convert_amount(1000, "usd", "usd")
        assert result["converted_amount_cents"] == 1000
        assert result["conversion_applied"] is False

    def test_usd_to_eur(self):
        result = convert_amount(1000, "usd", "eur")
        assert result["converted_amount_cents"] == 920
        assert result["conversion_applied"] is True
        assert result["exchange_rate"] == "0.92"

    def test_usd_to_gbp(self):
        result = convert_amount(5000, "usd", "gbp")
        assert result["converted_amount_cents"] == 3950

    def test_eur_to_usd(self):
        result = convert_amount(1000, "eur", "usd")
        assert result["converted_amount_cents"] > 1000

    def test_jpy_conversion_no_decimals(self):
        result = convert_amount(1000, "usd", "jpy")
        assert isinstance(result["converted_amount_cents"], int)
        assert result["converted_amount_cents"] == 149500

    def test_negative_amount_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            convert_amount(-100, "usd", "eur")

    def test_zero_amount(self):
        result = convert_amount(0, "usd", "eur")
        assert result["converted_amount_cents"] == 0

    def test_rounding(self):
        result = convert_amount(333, "usd", "eur")
        assert isinstance(result["converted_amount_cents"], int)

    def test_large_amount(self):
        result = convert_amount(10_000_000, "usd", "eur")
        assert result["converted_amount_cents"] == 9_200_000


class TestSupportedCurrencies:
    def test_base_currency_supported(self):
        assert BASE_CURRENCY in SUPPORTED_CURRENCIES

    def test_major_currencies_supported(self):
        for currency in ("usd", "eur", "gbp"):
            assert currency in SUPPORTED_CURRENCIES

    def test_all_currencies_lowercase(self):
        for currency in SUPPORTED_CURRENCIES:
            assert currency == currency.lower()


class TestConversionMetadata:
    @patch("src.payments.currency.get_db_connection")
    def test_store_and_retrieve_metadata(self, mock_get_conn):
        from src.payments.currency import _store_conversion_metadata, get_conversion_metadata

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_get_conn.return_value = mock_conn

        _store_conversion_metadata(
            payment_id=1,
            original_amount_cents=1000,
            original_currency="usd",
            converted_amount_cents=920,
            target_currency="eur",
            exchange_rate="0.92",
        )
        mock_cursor.execute.assert_called_once()

        mock_cursor.fetchone.return_value = {
            "payment_id": 1,
            "original_currency": "usd",
            "target_currency": "eur",
        }
        result = get_conversion_metadata(1)
        assert result["payment_id"] == 1
