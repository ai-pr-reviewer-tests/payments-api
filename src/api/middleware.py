"""API middleware for cross-cutting concerns."""

from functools import wraps

from flask import request, jsonify, g

from src.cache.rate_limiter import check_rate_limit


def rate_limit(endpoint: str = "default"):
    """Decorator that enforces rate limiting on an endpoint."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Use user ID if authenticated, otherwise IP
            identifier = getattr(g, "current_user_id", None)
            if identifier is None:
                identifier = request.remote_addr or "unknown"
            else:
                identifier = str(identifier)

            allowed, info = check_rate_limit(identifier, endpoint)

            if not allowed:
                response = jsonify({
                    "error": "Rate limit exceeded",
                    "retry_after": info["reset"],
                })
                response.status_code = 429
                response.headers["X-RateLimit-Limit"] = str(info["limit"])
                response.headers["X-RateLimit-Remaining"] = "0"
                response.headers["X-RateLimit-Reset"] = str(info["reset"])
                return response

            # Add rate limit headers to successful responses
            result = f(*args, **kwargs)
            if hasattr(result, "headers"):
                result.headers["X-RateLimit-Limit"] = str(info["limit"])
                result.headers["X-RateLimit-Remaining"] = str(info["remaining"])
                result.headers["X-RateLimit-Reset"] = str(info["reset"])

            return result
        return decorated
    return decorator
