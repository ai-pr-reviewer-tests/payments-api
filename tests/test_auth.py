"""Tests for authentication module."""

import pytest
from unittest.mock import patch
import os

os.environ["JWT_SECRET_KEY"] = "test-secret"

from src.auth.jwt_handler import create_token, verify_token
from src.auth.permissions import Role


class TestJWT:
    def test_create_and_verify_token(self):
        token = create_token(user_id=42, role="user")
        payload = verify_token(token)
        assert payload["sub"] == 42
        assert payload["role"] == "user"

    def test_expired_token_raises(self):
        import jwt as pyjwt
        from datetime import datetime, timedelta, timezone
        payload = {
            "sub": 1,
            "role": "user",
            "iat": datetime.now(timezone.utc) - timedelta(hours=48),
            "exp": datetime.now(timezone.utc) - timedelta(hours=24),
        }
        token = pyjwt.encode(payload, "test-secret", algorithm="HS256")
        with pytest.raises(pyjwt.ExpiredSignatureError):
            verify_token(token)

    def test_invalid_token_raises(self):
        import jwt as pyjwt
        with pytest.raises(pyjwt.InvalidTokenError):
            verify_token("not.a.token")


class TestRoles:
    def test_role_hierarchy(self):
        assert Role.USER.level() < Role.SUPPORT.level()
        assert Role.SUPPORT.level() < Role.ADMIN.level()

    def test_role_from_string(self):
        assert Role("admin") == Role.ADMIN
        assert Role("user") == Role.USER
