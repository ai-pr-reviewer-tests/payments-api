"""Retry utilities for external service calls."""
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)


def retry(max_attempts: int = 3, delay: float = 1.0,
          backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """Decorator that retries a function on failure with exponential backoff."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return f(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        logger.warning(
                            "Attempt %d/%d for %s failed: %s. Retrying in %.1fs",
                            attempt, max_attempts, f.__name__, str(e), current_delay,
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            "All %d attempts for %s failed: %s",
                            max_attempts, f.__name__, str(e),
                        )
            
            raise last_exception
        return wrapper
    return decorator
