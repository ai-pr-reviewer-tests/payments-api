"""Session management backed by Redis."""

from src.cache.redis_client import get_redis


SESSION_PREFIX = "session:"
SESSION_TTL = 259200  # 72 hours


def create_session(user_id: int, token: str) -> None:
    """Store a session in Redis."""
    r = get_redis()
    r.setex(f"{SESSION_PREFIX}{user_id}", SESSION_TTL, token)


def get_session(user_id: int) -> str | None:
    """Retrieve active session token for a user."""
    r = get_redis()
    val = r.get(f"{SESSION_PREFIX}{user_id}")
    return val.decode("utf-8") if val else None


def revoke_session(user_id: int) -> None:
    """Delete the user's session."""
    r = get_redis()
    r.delete(f"{SESSION_PREFIX}{user_id}")
