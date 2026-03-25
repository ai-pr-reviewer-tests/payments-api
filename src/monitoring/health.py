"""Health check utilities."""
import logging
from src.db.connection import get_db_connection
from src.cache.redis_client import get_redis

logger = logging.getLogger(__name__)


def check_database() -> dict:
    """Check database connectivity."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        logger.error("Database health check failed: %s", str(e))
        return {"status": "unhealthy", "error": str(e)}


def check_redis() -> dict:
    """Check Redis connectivity."""
    try:
        r = get_redis()
        r.ping()
        return {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        logger.error("Redis health check failed: %s", str(e))
        return {"status": "unhealthy", "error": str(e)}


def check_all() -> dict:
    """Run all health checks."""
    return {
        "database": check_database(),
        "redis": check_redis(),
    }
