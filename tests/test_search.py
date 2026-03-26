"""Tests for user search functionality."""

import pytest
from unittest.mock import patch, MagicMock

from src.db.search import (
    search_users,
    get_user_details,
    search_users_by_payment_activity,
    SORTABLE_FIELDS,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)


def _mock_cursor_factory(fetchone_result=None, fetchall_result=None):
    """Create a mock connection with a cursor that returns specified results."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    if fetchone_result is not None:
        mock_cursor.fetchone.return_value = fetchone_result
    if fetchall_result is not None:
        mock_cursor.fetchall.return_value = fetchall_result
    return mock_conn, mock_cursor


class TestSearchUsers:
    @patch("src.db.search.get_db_connection")
    def test_basic_search_no_filters(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_cursor_factory(
            fetchone_result={"total": 2},
            fetchall_result=[
                {"id": 1, "email": "alice@example.com", "role": "user"},
                {"id": 2, "email": "bob@example.com", "role": "admin"},
            ],
        )
        mock_get_conn.return_value = mock_conn

        result = search_users()

        assert result["total"] == 2
        assert len(result["users"]) == 2
        assert result["page"] == 1
        assert result["page_size"] == DEFAULT_PAGE_SIZE

    @patch("src.db.search.get_db_connection")
    def test_search_with_text_query(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_cursor_factory(
            fetchone_result={"total": 1},
            fetchall_result=[
                {"id": 1, "email": "alice@example.com", "role": "user"},
            ],
        )
        mock_get_conn.return_value = mock_conn

        result = search_users(query_text="alice")

        assert result["total"] == 1
        calls = mock_cursor.execute.call_args_list
        count_query_params = calls[0][0][1]
        assert "%alice%" in count_query_params

    @patch("src.db.search.get_db_connection")
    def test_search_with_role_filter(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_cursor_factory(
            fetchone_result={"total": 5},
            fetchall_result=[],
        )
        mock_get_conn.return_value = mock_conn

        result = search_users(role="admin")

        assert result["total"] == 5
        calls = mock_cursor.execute.call_args_list
        count_query_params = calls[0][0][1]
        assert "admin" in count_query_params

    @patch("src.db.search.get_db_connection")
    def test_pagination_offset_calculation(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_cursor_factory(
            fetchone_result={"total": 100},
            fetchall_result=[],
        )
        mock_get_conn.return_value = mock_conn

        result = search_users(page=3, page_size=10)

        assert result["page"] == 3
        assert result["page_size"] == 10
        assert result["total_pages"] == 10
        data_query_params = mock_cursor.execute.call_args_list[1][0][1]
        assert 10 in data_query_params
        assert 20 in data_query_params

    @patch("src.db.search.get_db_connection")
    def test_page_size_clamped_to_max(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_cursor_factory(
            fetchone_result={"total": 0},
            fetchall_result=[],
        )
        mock_get_conn.return_value = mock_conn

        result = search_users(page_size=500)

        assert result["page_size"] == MAX_PAGE_SIZE

    @patch("src.db.search.get_db_connection")
    def test_invalid_sort_field_uses_default(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_cursor_factory(
            fetchone_result={"total": 0},
            fetchall_result=[],
        )
        mock_get_conn.return_value = mock_conn

        result = search_users(sort_by="nonexistent_column")

        data_query = mock_cursor.execute.call_args_list[1][0][0]
        assert "created_at" in data_query

    @patch("src.db.search.get_db_connection")
    def test_sort_ascending(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_cursor_factory(
            fetchone_result={"total": 3},
            fetchall_result=[
                {"id": 1, "email": "a@test.com"},
                {"id": 2, "email": "b@test.com"},
                {"id": 3, "email": "c@test.com"},
            ],
        )
        mock_get_conn.return_value = mock_conn

        result = search_users(sort_by="email", sort_dir="ASC")

        assert result["total"] == 3

    def test_sortable_fields_defined(self):
        assert "email" in SORTABLE_FIELDS
        assert "created_at" in SORTABLE_FIELDS
        assert "role" in SORTABLE_FIELDS
        assert "last_login" in SORTABLE_FIELDS


class TestGetUserDetails:
    @patch("src.db.search.get_db_connection")
    def test_existing_user(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_cursor_factory(
            fetchone_result={
                "id": 42,
                "email": "test@example.com",
                "display_name": "Test User",
                "role": "user",
                "email_verified": True,
                "account_status": "active",
            },
        )
        mock_get_conn.return_value = mock_conn

        result = get_user_details(42)

        assert result is not None
        assert result["id"] == 42
        assert result["email"] == "test@example.com"

    @patch("src.db.search.get_db_connection")
    def test_nonexistent_user(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_cursor_factory(fetchone_result=None)
        mock_get_conn.return_value = mock_conn

        result = get_user_details(999)

        assert result is None


class TestPaymentActivitySearch:
    @patch("src.db.search.get_db_connection")
    def test_search_active_users(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_cursor_factory(
            fetchone_result={"total": 15},
            fetchall_result=[
                {"id": 1, "email": "big@spender.com", "payment_count": 20, "total_spent": 500000},
            ],
        )
        mock_get_conn.return_value = mock_conn

        result = search_users_by_payment_activity(min_payments=5)

        assert result["total"] == 15

    @patch("src.db.search.get_db_connection")
    def test_search_with_min_total(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_cursor_factory(
            fetchone_result={"total": 3},
            fetchall_result=[],
        )
        mock_get_conn.return_value = mock_conn

        result = search_users_by_payment_activity(
            min_payments=1, min_total_cents=10000,
        )

        assert result["total"] == 3

    @patch("src.db.search.get_db_connection")
    def test_invalid_sort_field_defaults(self, mock_get_conn):
        mock_conn, mock_cursor = _mock_cursor_factory(
            fetchone_result={"total": 0},
            fetchall_result=[],
        )
        mock_get_conn.return_value = mock_conn

        result = search_users_by_payment_activity(sort_by="invalid_field")

        data_query = mock_cursor.execute.call_args_list[1][0][0]
        assert "total_spent" in data_query
