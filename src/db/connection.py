"""Database connection management."""

import os

import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = os.environ.get("DATABASE_URL", "")

_connection = None


def get_db_connection():
    """Return a database connection, creating one if needed."""
    global _connection
    if _connection is None or _connection.closed:
        _connection = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        _connection.autocommit = True
    return _connection


def close_db_connection():
    """Close the database connection."""
    global _connection
    if _connection and not _connection.closed:
        _connection.close()
        _connection = None
