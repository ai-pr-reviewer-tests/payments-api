"""Distributed rate limiting using Redis.

Implements a sliding window rate limiter for API endpoints.
"""

import time
import logging

from src.cache.redis_client import get_redis

logger = logging.getLogger(__name__)

# Rate limit configuration: (max_requests, window_seconds)
RATE_LIMITS = {
    "default": (100, 60),          # 100 req/min
    "auth_login": (5, 60),         # 5 req/min (brute force protection)
    "payments_charge": (10, 60),   # 10 req/min
}

RATE_LIMIT_PREFIX = "ratelimit:"


def check_rate_limit(identifier: str, endpoint: str = "default") -> tuple[bool, dict]:
    """Check if a request is within the rate limit.

    Args:
        identifier: Unique identifier (e.g., user ID, IP address).
        endpoint: The endpoint category for limit lookup.

    Returns:
        Tuple of (allowed: bool, info: dict with limit, remaining, reset).
    """
    max_requests, window = RATE_LIMITS.get(endpoint, RATE_LIMITS["default"])
    key = f"{RATE_LIMIT_PREFIX}{endpoint}:{identifier}"

    r = get_redis()
    now = time.time()

    # BUG: Race condition — read-modify-write is not atomic
    # Two concurrent requests can both read the same count,
    # both decide they're under the limit, and both increment,
    # allowing more requests through than the limit allows
    current_count = r.get(key)

    if current_count is None:
        # First request in this window
        r.setex(key, window, 1)
        return True, {
            "limit": max_requests,
            "remaining": max_requests - 1,
            "reset": int(now + window),
        }

    count = int(current_count)

    if count >= max_requests:
        ttl = r.ttl(key)
        return False, {
            "limit": max_requests,
            "remaining": 0,
            "reset": int(now + ttl),
        }

    # BUG: Non-atomic increment — another request could have incremented
    # between our GET and this SET, losing that increment
    r.set(key, count + 1, keepttl=True)

    return True, {
        "limit": max_requests,
        "remaining": max_requests - count - 1,
        "reset": int(now + r.ttl(key)),
    }
