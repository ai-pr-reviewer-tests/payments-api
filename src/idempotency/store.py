"""Idempotency key storage and management.

Provides database-backed idempotency key tracking to prevent duplicate
payment processing. Each idempotency key is stored with its associated
response so that repeated requests return the same result.
"""

import json
import logging
from datetime import datetime, timezone, timedelta

from src.db.connection import get_db_connection

logger = logging.getLogger(__name__)

# Idempotency keys expire after 24 hours
KEY_TTL_HOURS = 24


class IdempotencyKeyError(Exception):
    """Raised when there's an issue with idempotency key processing."""
    pass


class IdempotencyStore:
    """Manages idempotency keys in the database.

    Keys are stored with their request fingerprint and cached response.
    After TTL expiration, keys can be reused.
    """

    def __init__(self):
        self._ttl = timedelta(hours=KEY_TTL_HOURS)

    def get_existing(self, key: str) -> dict | None:
        """Look up an existing idempotency key and its stored response.

        Args:
            key: The idempotency key from the request header.

        Returns:
            The stored response dict if the key exists and hasn't expired,
            None if the key doesn't exist or has expired.
        """
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """SELECT key, request_path, request_fingerprint,
                          response_code, response_body, created_at
                   FROM idempotency_keys
                   WHERE key = %s""",
                (key,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        # Check if the key has expired
        created_at = row["created_at"]
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)

        if datetime.now(timezone.utc) - created_at.replace(tzinfo=timezone.utc) > self._ttl:
            logger.info("Idempotency key %s has expired, allowing reuse", key[:8])
            self._delete_key(key)
            return None

        return {
            "key": row["key"],
            "request_path": row["request_path"],
            "request_fingerprint": row["request_fingerprint"],
            "response_code": row["response_code"],
            "response_body": json.loads(row["response_body"]),
            "created_at": str(row["created_at"]),
        }

    def store_response(
        self,
        key: str,
        request_path: str,
        request_fingerprint: str,
        response_code: int,
        response_body: dict,
    ) -> None:
        """Store the response for an idempotency key.

        Args:
            key: The idempotency key.
            request_path: The API path that was called.
            request_fingerprint: Hash of the request body for consistency checking.
            response_code: HTTP status code of the response.
            response_body: Response body to cache.
        """
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO idempotency_keys
                   (key, request_path, request_fingerprint, response_code, response_body, created_at)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    key,
                    request_path,
                    request_fingerprint,
                    response_code,
                    json.dumps(response_body),
                    datetime.now(timezone.utc),
                ),
            )

    def _delete_key(self, key: str) -> None:
        """Remove an expired idempotency key."""
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM idempotency_keys WHERE key = %s", (key,))

    def cleanup_expired(self) -> int:
        """Remove all expired idempotency keys.

        Returns:
            Number of keys removed.
        """
        cutoff = datetime.now(timezone.utc) - self._ttl
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM idempotency_keys WHERE created_at < %s",
                (cutoff,),
            )
            return cur.rowcount
