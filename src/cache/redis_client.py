"""Redis client singleton."""

import os

import redis

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

_client = None


def get_redis() -> redis.Redis:
    """Return the Redis client, creating one if needed."""
    global _client
    if _client is None:
        _client = redis.from_url(REDIS_URL, decode_responses=False)
    return _client
