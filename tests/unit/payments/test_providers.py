"""Tests for payment providers."""
import pytest
from unittest.mock import patch, MagicMock
from src.payments.providers.base import ChargeStatus, ChargeResult
from src.payments.providers.stripe_provider import StripeProvider


class TestStripeProvider:
    def setup_method(self):
        self.provider = StripeProvider()
        self.provider.initialize({"api_key": "sk_test_fake", "webhook_secret": "whsec_test"})

    @patch("src.payments.providers.stripe_provider.stripe.Charge.create")
    def test_successful_charge(self, mock_create):
        mock_create.return_value = MagicMock(
            id="ch_test", status="succeeded", amount=1000, currency="usd"
        )
        result = self.provider.create_charge(1000, "usd", "tok_test")
        assert result.status == ChargeStatus.SUCCEEDED
        assert result.provider_charge_id == "ch_test"

    def test_supported_currencies(self):
        assert "usd" in self.provider.supported_currencies()
        assert "eur" in self.provider.supported_currencies()


class TestBraintreeProvider:
    def test_not_implemented(self):
        from src.payments.providers.braintree_provider import BraintreeProvider
        provider = BraintreeProvider()
        provider.initialize({})
        with pytest.raises(NotImplementedError):
            provider.create_charge(1000, "usd", "tok_test")


class TestAdyenProvider:
    def test_not_implemented(self):
        from src.payments.providers.adyen_provider import AdyenProvider
        provider = AdyenProvider()
        provider.initialize({})
        with pytest.raises(NotImplementedError):
            provider.create_charge(1000, "usd", "tok_test")
