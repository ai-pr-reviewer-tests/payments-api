"""Webhook signature verification for incoming payment events.

Implements Stripe-style HMAC-SHA256 signature verification to ensure
webhook payloads are authentic and have not been tampered with.

The expected signature format is:
    t=<timestamp>,v1=<hex_signature>

Where the signed payload is constructed as:
    <timestamp>.<raw_body>
"""

import hashlib
import hmac
import time
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

DEFAULT_TOLERANCE = 300  # 5 minutes


@dataclass
class VerificationResult:
    """Result of a signature verification attempt."""
    valid: bool
    event_timestamp: int | None = None
    error: str | None = None


def compute_signature(payload: bytes, secret: str, timestamp: int) -> str:
    """Compute the expected HMAC-SHA256 signature for a payload.

    Args:
        payload: Raw request body bytes.
        secret: The webhook signing secret.
        timestamp: Unix timestamp included in the signature header.

    Returns:
        Hex-encoded HMAC-SHA256 signature string.
    """
    signed_payload = f"{timestamp}.".encode() + payload
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=signed_payload,
        digestmod=hashlib.sha256,
    ).hexdigest()


def parse_signature_header(header: str) -> tuple[int | None, str | None]:
    """Parse the webhook signature header into timestamp and signature.

    Expected format: t=<unix_timestamp>,v1=<hex_signature>

    Args:
        header: Raw signature header string.

    Returns:
        Tuple of (timestamp, signature) or (None, None) if parsing fails.
    """
    timestamp = None
    signature = None

    if not header:
        return None, None

    for element in header.split(","):
        key_value = element.strip().split("=", 1)
        if len(key_value) != 2:
            continue

        key, value = key_value
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError:
                return None, None
        elif key == "v1":
            signature = value

    return timestamp, signature


def verify_signature(
    payload: bytes,
    signature_header: str,
    secret: str,
    tolerance: int = DEFAULT_TOLERANCE,
) -> VerificationResult:
    """Verify the webhook signature against the payload.

    Checks that:
    1. The signature header is well-formed
    2. The computed signature matches the provided one
    3. The timestamp is within the tolerance window (replay protection)

    Args:
        payload: Raw request body as bytes.
        signature_header: Value of the Stripe-Signature header.
        secret: The webhook signing secret (from Stripe dashboard).
        tolerance: Maximum age of the event in seconds.

    Returns:
        VerificationResult indicating whether verification succeeded.
    """
    timestamp, received_sig = parse_signature_header(signature_header)

    if timestamp is None or received_sig is None:
        logger.warning("Webhook signature header is malformed")
        return VerificationResult(
            valid=False,
            error="Invalid signature header format",
        )

    expected_sig = compute_signature(payload, secret, timestamp)

    if expected_sig == received_sig:
        # Check timestamp freshness to prevent replay attacks
        current_time = int(time.time())
        age = abs(current_time - timestamp)

        if age > tolerance:
            logger.warning(
                "Webhook timestamp too old: %d seconds (tolerance: %d)",
                age,
                tolerance,
            )
            return VerificationResult(
                valid=False,
                event_timestamp=timestamp,
                error="Timestamp outside tolerance window",
            )

        return VerificationResult(valid=True, event_timestamp=timestamp)

    logger.warning("Webhook signature mismatch")
    return VerificationResult(
        valid=False,
        event_timestamp=timestamp,
        error="Signature verification failed",
    )
