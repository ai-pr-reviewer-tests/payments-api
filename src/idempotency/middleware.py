"""Idempotency middleware for payment creation endpoints.

Intercepts requests with an Idempotency-Key header to prevent duplicate
payment processing. If a key has been seen before, returns the cached
response instead of reprocessing.
"""

import hashlib
import json
import logging
from functools import wraps

from flask import request, jsonify, g

from src.idempotency.store import IdempotencyStore, IdempotencyKeyError

logger = logging.getLogger(__name__)

_store = IdempotencyStore()

# Maximum length for idempotency keys
MAX_KEY_LENGTH = 255

# Minimum length for idempotency keys
MIN_KEY_LENGTH = 8


def compute_request_fingerprint(body: dict, path: str) -> str:
    """Compute a fingerprint for a request to detect mismatched retries.

    If the same idempotency key is used with different request bodies,
    this fingerprint will differ, allowing us to reject the request.

    Args:
        body: The parsed request body.
        path: The request path.

    Returns:
        Hex digest of the request fingerprint.
    """
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    content = f"{path}:{canonical}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def require_idempotency_key(f):
    """Decorator that enforces idempotency key handling on an endpoint.

    When an Idempotency-Key header is present:
    1. Check if we've already processed a request with this key
    2. If yes, verify the request body matches and return the cached response
    3. If no, process the request and cache the response

    When the header is absent, the request is processed normally (no
    idempotency enforcement). This matches Stripe's behavior where the
    key is optional.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        idempotency_key = request.headers.get("Idempotency-Key")

        if not idempotency_key:
            return f(*args, **kwargs)

        # Validate key format
        if len(idempotency_key) < MIN_KEY_LENGTH:
            return jsonify({
                "error": "Idempotency key too short",
                "min_length": MIN_KEY_LENGTH,
            }), 400

        if len(idempotency_key) > MAX_KEY_LENGTH:
            return jsonify({
                "error": "Idempotency key too long",
                "max_length": MAX_KEY_LENGTH,
            }), 400

        body = request.get_json(silent=True) or {}
        path = request.path
        fingerprint = compute_request_fingerprint(body, path)

        # Check for an existing response with this key
        existing = _store.get_existing(idempotency_key)

        if existing is not None:
            # Verify the request is consistent with the original
            if existing["request_fingerprint"] != fingerprint:
                logger.warning(
                    "Idempotency key %s reused with different request body",
                    idempotency_key[:8],
                )
                return jsonify({
                    "error": "Idempotency key already used with different parameters",
                }), 422

            logger.info(
                "Returning cached response for idempotency key %s",
                idempotency_key[:8],
            )
            return jsonify(existing["response_body"]), existing["response_code"]

        # Process the request
        response = f(*args, **kwargs)

        # Extract response data for caching
        if isinstance(response, tuple):
            response_obj, status_code = response
        else:
            response_obj = response
            status_code = 200

        if hasattr(response_obj, "get_json"):
            response_body = response_obj.get_json()
        elif isinstance(response_obj, dict):
            response_body = response_obj
        else:
            response_body = {"data": str(response_obj)}

        # Store the response for future requests with the same key
        try:
            _store.store_response(
                key=idempotency_key,
                request_path=path,
                request_fingerprint=fingerprint,
                response_code=status_code,
                response_body=response_body,
            )
        except Exception as e:
            # Don't fail the request if caching fails — the payment
            # already went through. Log and continue.
            logger.error(
                "Failed to store idempotency key %s: %s",
                idempotency_key[:8], str(e),
            )

        return response

    return decorated
