"""Payment test fixtures."""
import pytest


SAMPLE_CHARGE_DATA = {
    "amount_cents": 5000,
    "currency": "usd",
    "source_token": "tok_visa",
    "description": "Test charge",
}

SAMPLE_REFUND_DATA = {
    "amount_cents": 2500,
}

SAMPLE_STRIPE_CHARGE_RESPONSE = {
    "id": "ch_test_123",
    "status": "succeeded",
    "amount": 5000,
    "currency": "usd",
}

SAMPLE_STRIPE_REFUND_RESPONSE = {
    "id": "re_test_123",
    "status": "succeeded",
    "amount": 2500,
}


@pytest.fixture
def charge_data():
    return SAMPLE_CHARGE_DATA.copy()


@pytest.fixture
def refund_data():
    return SAMPLE_REFUND_DATA.copy()
