"""Application-level caching utilities."""

import json
import logging
from typing import Any

from src.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

DEFAULT_TTL = 300  # 5 minutes

# TTL overrides per cache key prefix
TTL_CONFIG = {
    "user_profile": 600,      # 10 minutes
    "payment_details": 120,   # 2 minutes
    "user_payments": 60,      # 1 minute
}


def _format_cache_key(prefix: str, identifier: str) -> str:
    """Format a cache key from prefix and identifier."""
    return f"cache:{prefix}:{identifier}"


def cached(prefix: str, identifier: str) -> Any | None:
    """Retrieve a value from cache. Returns None on miss."""
    r = get_redis()
    key = _format_cache_key(prefix, identifier)
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
    key = _format_cache_key(prefix, identifier)
    ttl = TTL_CONFIG.get(prefix, DEFAULT_TTL)
    r.setex(key, ttl, json.dumps(value))


def invalidate(prefix: str, identifier: str) -> None:
    """Remove a specific entry from the cache."""
    r = get_redis()
    key = _format_cache_key(prefix, identifier)
    r.delete(key)
