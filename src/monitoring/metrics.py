"""Application metrics collection."""
import time
import logging
from functools import wraps

logger = logging.getLogger(__name__)

_metrics: dict[str, list] = {}


def record_metric(name: str, value: float, tags: dict | None = None) -> None:
    """Record a metric data point."""
    if name not in _metrics:
        _metrics[name] = []
    _metrics[name].append({
        "value": value,
        "timestamp": time.time(),
        "tags": tags or {},
    })


def get_metrics(name: str) -> list:
    """Retrieve recorded metrics."""
    return _metrics.get(name, [])


def clear_metrics() -> None:
    """Clear all recorded metrics."""
    _metrics.clear()


def timed(metric_name: str):
    """Decorator that records execution time."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start
                record_metric(metric_name, duration, {"status": "success"})
                return result
            except Exception as e:
                duration = time.time() - start
                record_metric(metric_name, duration, {"status": "error"})
                raise
        return wrapper
    return decorator
