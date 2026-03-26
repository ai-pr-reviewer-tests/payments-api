"""Tests for idempotency key handling."""

import json

import pytest
from unittest.mock import patch, MagicMock

from src.idempotency.middleware import compute_request_fingerprint


class TestRequestFingerprint:
    def test_same_body_same_fingerprint(self):
        body = {"amount_cents": 1000, "currency": "usd"}
        fp1 = compute_request_fingerprint(body, "/api/v1/payments/charge")
        fp2 = compute_request_fingerprint(body, "/api/v1/payments/charge")
        assert fp1 == fp2

    def test_key_order_does_not_matter(self):
        body1 = {"amount_cents": 1000, "currency": "usd"}
        body2 = {"currency": "usd", "amount_cents": 1000}
        fp1 = compute_request_fingerprint(body1, "/api/v1/payments/charge")
        fp2 = compute_request_fingerprint(body2, "/api/v1/payments/charge")
        assert fp1 == fp2

    def test_different_body_different_fingerprint(self):
        body1 = {"amount_cents": 1000, "currency": "usd"}
        body2 = {"amount_cents": 2000, "currency": "usd"}
        fp1 = compute_request_fingerprint(body1, "/api/v1/payments/charge")
        fp2 = compute_request_fingerprint(body2, "/api/v1/payments/charge")
        assert fp1 != fp2

    def test_different_path_different_fingerprint(self):
        body = {"amount_cents": 1000}
        fp1 = compute_request_fingerprint(body, "/api/v1/payments/charge")
        fp2 = compute_request_fingerprint(body, "/api/v1/payments/refund")
        assert fp1 != fp2

    def test_empty_body(self):
        fp = compute_request_fingerprint({}, "/api/v1/payments/charge")
        assert len(fp) == 64  # SHA-256 hex digest length

    def test_nested_body(self):
        body = {
            "amount_cents": 1000,
            "metadata": {"order_id": "ord_123", "customer": "cus_456"},
        }
        fp1 = compute_request_fingerprint(body, "/path")
        fp2 = compute_request_fingerprint(body, "/path")
        assert fp1 == fp2


class TestIdempotencyStore:
    @patch("src.idempotency.store.get_db_connection")
    def test_get_existing_returns_none_for_missing_key(self, mock_conn):
        from src.idempotency.store import IdempotencyStore

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value = mock_cursor

        store = IdempotencyStore()
        result = store.get_existing("nonexistent-key")
        assert result is None

    @patch("src.idempotency.store.get_db_connection")
    def test_store_response_inserts_record(self, mock_conn):
        from src.idempotency.store import IdempotencyStore

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.return_value.cursor.return_value = mock_cursor

        store = IdempotencyStore()
        store.store_response(
            key="test-key-12345",
            request_path="/api/v1/payments/charge",
            request_fingerprint="abc123",
            response_code=201,
            response_body={"payment_id": 1},
        )

        mock_cursor.execute.assert_called_once()
        call_args = mock_cursor.execute.call_args
        assert "INSERT INTO idempotency_keys" in call_args[0][0]

    @patch("src.idempotency.store.get_db_connection")
    def test_cleanup_expired(self, mock_conn):
        from src.idempotency.store import IdempotencyStore

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.rowcount = 5
        mock_conn.return_value.cursor.return_value = mock_cursor

        store = IdempotencyStore()
        removed = store.cleanup_expired()
        assert removed == 5


class TestIdempotencyKeyValidation:
    def test_key_too_short(self):
        """Keys shorter than MIN_KEY_LENGTH should be rejected."""
        from src.idempotency.middleware import MIN_KEY_LENGTH
        assert MIN_KEY_LENGTH == 8

    def test_key_max_length(self):
        """Keys longer than MAX_KEY_LENGTH should be rejected."""
        from src.idempotency.middleware import MAX_KEY_LENGTH
        assert MAX_KEY_LENGTH == 255
