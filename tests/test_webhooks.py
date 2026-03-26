"""Tests for webhook signature verification and event processing."""

import hashlib
import hmac
import json
import time

import pytest

from src.webhooks.signature import (
    compute_signature,
    parse_signature_header,
    verify_signature,
    VerificationResult,
)


class TestParseSignatureHeader:
    def test_valid_header(self):
        ts, sig = parse_signature_header("t=1234567890,v1=abc123def456")
        assert ts == 1234567890
        assert sig == "abc123def456"

    def test_empty_header(self):
        ts, sig = parse_signature_header("")
        assert ts is None
        assert sig is None

    def test_missing_timestamp(self):
        ts, sig = parse_signature_header("v1=abc123")
        assert ts is None
        assert sig == "abc123"

    def test_missing_signature(self):
        ts, sig = parse_signature_header("t=1234567890")
        assert ts == 1234567890
        assert sig is None

    def test_invalid_timestamp(self):
        ts, sig = parse_signature_header("t=notanumber,v1=abc123")
        assert ts is None
        assert sig is None

    def test_whitespace_handling(self):
        ts, sig = parse_signature_header("t=1234567890, v1=abc123def456")
        assert ts == 1234567890
        assert sig == "abc123def456"


class TestComputeSignature:
    def test_deterministic(self):
        sig1 = compute_signature(b"test payload", "secret", 1234567890)
        sig2 = compute_signature(b"test payload", "secret", 1234567890)
        assert sig1 == sig2

    def test_different_payload_different_sig(self):
        sig1 = compute_signature(b"payload A", "secret", 1234567890)
        sig2 = compute_signature(b"payload B", "secret", 1234567890)
        assert sig1 != sig2

    def test_different_secret_different_sig(self):
        sig1 = compute_signature(b"test", "secret1", 1234567890)
        sig2 = compute_signature(b"test", "secret2", 1234567890)
        assert sig1 != sig2

    def test_different_timestamp_different_sig(self):
        sig1 = compute_signature(b"test", "secret", 1000000000)
        sig2 = compute_signature(b"test", "secret", 2000000000)
        assert sig1 != sig2


class TestVerifySignature:
    def _make_signature(self, payload: bytes, secret: str, timestamp: int) -> str:
        """Helper to create a valid signature header."""
        sig = compute_signature(payload, secret, timestamp)
        return f"t={timestamp},v1={sig}"

    def test_valid_signature(self):
        payload = b'{"type": "charge.succeeded"}'
        secret = "whsec_test_secret_key"
        timestamp = int(time.time())

        header = self._make_signature(payload, secret, timestamp)
        result = verify_signature(payload, header, secret)

        assert result.valid is True
        assert result.event_timestamp == timestamp
        assert result.error is None

    def test_invalid_signature(self):
        payload = b'{"type": "charge.succeeded"}'
        secret = "whsec_test_secret_key"
        timestamp = int(time.time())

        header = f"t={timestamp},v1=invalidsignaturevalue"
        result = verify_signature(payload, header, secret)

        assert result.valid is False
        assert result.error == "Signature verification failed"

    def test_wrong_secret(self):
        payload = b'{"type": "charge.succeeded"}'
        timestamp = int(time.time())

        header = self._make_signature(payload, "correct_secret", timestamp)
        result = verify_signature(payload, header, "wrong_secret")

        assert result.valid is False

    def test_tampered_payload(self):
        original = b'{"amount": 1000}'
        secret = "whsec_test"
        timestamp = int(time.time())

        header = self._make_signature(original, secret, timestamp)
        tampered = b'{"amount": 9999}'
        result = verify_signature(tampered, header, secret)

        assert result.valid is False

    def test_expired_timestamp(self):
        payload = b'{"type": "charge.succeeded"}'
        secret = "whsec_test"
        old_timestamp = int(time.time()) - 600  # 10 minutes ago

        header = self._make_signature(payload, secret, old_timestamp)
        result = verify_signature(payload, header, secret, tolerance=300)

        assert result.valid is False
        assert "tolerance" in result.error.lower()

    def test_malformed_header(self):
        result = verify_signature(b"body", "garbage", "secret")
        assert result.valid is False
        assert result.error == "Invalid signature header format"

    def test_empty_header(self):
        result = verify_signature(b"body", "", "secret")
        assert result.valid is False

    def test_custom_tolerance(self):
        payload = b'{"type": "test"}'
        secret = "whsec_test"
        timestamp = int(time.time()) - 10

        header = self._make_signature(payload, secret, timestamp)
        result = verify_signature(payload, header, secret, tolerance=5)

        assert result.valid is False

    def test_future_timestamp_within_tolerance(self):
        payload = b'{"type": "test"}'
        secret = "whsec_test"
        timestamp = int(time.time()) + 60

        header = self._make_signature(payload, secret, timestamp)
        result = verify_signature(payload, header, secret, tolerance=300)

        assert result.valid is True
