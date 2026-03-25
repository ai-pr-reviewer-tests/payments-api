"""Application-level caching utilities."""

import json
import logging
from typing import Any

from src.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

DEFAULT_TTL = 300  # 5 minutes

# TTL overrides per cache key prefix (in seconds)
# Updated: tuned based on production access patterns
TTL_CONFIG = {
    "user_profile": 900,       # 15 minutes (was 10m — profiles rarely change)
    "payment_details": 300,    # 5 minutes (was 2m — reduce Stripe API calls)
    "user_payments": 120,      # 2 minutes (was 1m — listing is expensive)
    "session_data": 0,         # sessions managed by auth layer, no TTL needed
}


def _build_key(prefix: str, identifier: str) -> str:
    return f"cache:{prefix}:{identifier}"


def cached(prefix: str, identifier: str) -> Any | None:
    """Retrieve a value from cache. Returns None on miss."""
    r = get_redis()
    key = _build_key(prefix, identifier)
    raw = r.get(key)
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Corrupt cache entry for %s, deleting", key)
        r.delete(key)
        return None


def set_cached(prefix: str, identifier: str, value: Any) -> None:
    """Store a value in the cache with the appropriate TTL."""
    r = get_redis()
    key = _build_key(prefix, identifier)
    ttl = TTL_CONFIG.get(prefix, DEFAULT_TTL)
    if ttl == 0:
        # No expiry — persist until explicitly invalidated
        r.set(key, json.dumps(value))
    else:
        r.setex(key, ttl, json.dumps(value))


def invalidate(prefix: str, identifier: str) -> None:
    """Remove a specific entry from the cache."""
    r = get_redis()
    key = _build_key(prefix, identifier)
    r.delete(key)
