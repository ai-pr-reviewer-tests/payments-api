"""User test fixtures."""
import pytest


SAMPLE_USER = {
    "id": 1,
    "email": "test@example.com",
    "role": "user",
    "password_hash": "$2b$12$test_hash",
}

SAMPLE_ADMIN = {
    "id": 2,
    "email": "admin@example.com",
    "role": "admin",
    "password_hash": "$2b$12$admin_hash",
}


@pytest.fixture
def sample_user():
    return SAMPLE_USER.copy()


@pytest.fixture
def sample_admin():
    return SAMPLE_ADMIN.copy()
