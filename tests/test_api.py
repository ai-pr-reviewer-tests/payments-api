"""Tests for API endpoints."""

from unittest.mock import patch


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"


class TestAuthEndpoints:
    def test_login_missing_fields(self, client):
        resp = client.post("/api/v1/auth/login", json={})
        assert resp.status_code == 400

    def test_login_invalid_email(self, client):
        resp = client.post("/api/v1/auth/login", json={
            "email": "not-an-email",
            "password": "secret",
        })
        assert resp.status_code == 400

    def test_logout_requires_auth(self, client):
        resp = client.post("/api/v1/auth/logout")
        assert resp.status_code == 401


class TestPaymentEndpoints:
    def test_charge_requires_auth(self, client):
        resp = client.post("/api/v1/payments/charge", json={
            "amount_cents": 1000,
            "currency": "usd",
            "source_token": "tok_test",
        })
        assert resp.status_code == 401

    def test_get_payment_requires_auth(self, client):
        resp = client.get("/api/v1/payments/1")
        assert resp.status_code == 401


class TestUserEndpoints:
    def test_me_requires_auth(self, client):
        resp = client.get("/api/v1/users/me")
        assert resp.status_code == 401
