"""User search queries with pagination and sorting."""

import logging
from typing import Any

from src.db.connection import get_db_connection

logger = logging.getLogger(__name__)

SEARCHABLE_FIELDS = ("email", "role")
SORTABLE_FIELDS = ("email", "created_at", "role", "last_login")
DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def search_users(query_text: str | None = None, role: str | None = None,
                 sort_by: str = "created_at", sort_dir: str = "DESC",
                 page: int = 1, page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    """Search users with full-text filtering, pagination, and sorting.

    Args:
        query_text: Optional search string matched against email and name.
        role: Optional role filter (exact match).
        sort_by: Column to sort by. Must be in SORTABLE_FIELDS.
        sort_dir: Sort direction, ASC or DESC.
        page: Page number (1-indexed).
        page_size: Number of results per page.

    Returns:
        dict with users list, total count, and pagination metadata.
    """
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)
    page = max(1, page)
    offset = (page - 1) * page_size

    if sort_by not in SORTABLE_FIELDS:
        sort_by = "created_at"

    conditions = []
    params: list[Any] = []

    if query_text:
        conditions.append(
            "(email ILIKE %s OR display_name ILIKE %s)"
        )
        like_pattern = f"%{query_text}%"
        params.extend([like_pattern, like_pattern])

    if role:
        conditions.append("role = %s")
        params.append(role)

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    count_query = f"SELECT COUNT(*) AS total FROM users {where_clause}"
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(count_query, params)
        total = cur.fetchone()["total"]

    query = f"""
        SELECT id, email, display_name, role, created_at, last_login
        FROM users
        {where_clause}
        ORDER BY {sort_by} {sort_dir}
        LIMIT %s OFFSET %s
    """

    if sort_dir not in ("ASC", "DESC"):
        sort_dir = "ASC"

    search_params = params + [page_size, offset]
    with conn.cursor() as cur:
        cur.execute(query, search_params)
        users = cur.fetchall()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return {
        "users": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


def get_user_details(user_id: int) -> dict | None:
    """Retrieve detailed information for a single user.

    Args:
        user_id: The user's database ID.

    Returns:
        dict with user fields, or None if not found.
    """
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, email, display_name, role, created_at, last_login,
                      email_verified, account_status
               FROM users WHERE id = %s""",
            (user_id,),
        )
        return cur.fetchone()


def search_users_by_payment_activity(min_payments: int = 1,
                                     min_total_cents: int | None = None,
                                     sort_by: str = "total_spent",
                                     sort_dir: str = "DESC",
                                     page: int = 1,
                                     page_size: int = DEFAULT_PAGE_SIZE) -> dict:
    """Search users based on their payment activity.

    Args:
        min_payments: Minimum number of completed payments.
        min_total_cents: Minimum total amount spent in cents.
        sort_by: Column to sort by. Allowed: total_spent, payment_count, email.
        sort_dir: Sort direction, ASC or DESC.
        page: Page number.
        page_size: Results per page.

    Returns:
        dict with user payment activity, total count, and pagination.
    """
    page_size = min(max(1, page_size), MAX_PAGE_SIZE)
    page = max(1, page)
    offset = (page - 1) * page_size

    allowed_sort = ("total_spent", "payment_count", "email")
    if sort_by not in allowed_sort:
        sort_by = "total_spent"

    if sort_dir not in ("ASC", "DESC"):
        sort_dir = "DESC"

    having_clauses = ["COUNT(p.id) >= %s"]
    having_params: list[Any] = [min_payments]

    if min_total_cents is not None:
        having_clauses.append("COALESCE(SUM(p.amount_cents), 0) >= %s")
        having_params.append(min_total_cents)

    having_clause = " AND ".join(having_clauses)

    count_query = f"""
        SELECT COUNT(*) AS total FROM (
            SELECT u.id
            FROM users u
            LEFT JOIN payments p ON p.user_id = u.id AND p.status = 'completed'
            GROUP BY u.id
            HAVING {having_clause}
        ) subq
    """

    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(count_query, having_params)
        total = cur.fetchone()["total"]

    data_query = f"""
        SELECT u.id, u.email, u.display_name, u.role,
               COUNT(p.id) AS payment_count,
               COALESCE(SUM(p.amount_cents), 0) AS total_spent
        FROM users u
        LEFT JOIN payments p ON p.user_id = u.id AND p.status = 'completed'
        GROUP BY u.id, u.email, u.display_name, u.role
        HAVING {having_clause}
        ORDER BY {sort_by} {sort_dir}
        LIMIT %s OFFSET %s
    """

    query_params = having_params + [page_size, offset]
    with conn.cursor() as cur:
        cur.execute(data_query, query_params)
        users = cur.fetchall()

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1

    return {
        "users": users,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }
