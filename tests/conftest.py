"""Shared test fixtures."""

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_db():
    """Mock database connection and cursor."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    with patch("src.db.connection.get_db_connection", return_value=mock_conn):
        yield mock_cursor


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock_r = MagicMock()
    with patch("src.cache.redis_client.get_redis", return_value=mock_r):
        yield mock_r


@pytest.fixture
def app():
    """Create a Flask test app."""
    # Patch DB and Redis before importing app
    with patch("src.db.connection.get_db_connection"), \
         patch("src.cache.redis_client.get_redis"):
        from src.api.app import create_app
        import os
        os.environ["JWT_SECRET_KEY"] = "test-secret"
        app = create_app()
        app.config["TESTING"] = True
        yield app


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()
