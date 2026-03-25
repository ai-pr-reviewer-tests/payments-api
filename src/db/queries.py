"""Database query functions using parameterized queries."""

from src.db.connection import get_db_connection


def get_user_by_email(email: str) -> dict | None:
    """Look up a user by email address."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, password_hash, role FROM users WHERE email = %s",
            (email,),
        )
        return cur.fetchone()


def get_user_by_id(user_id: int) -> dict | None:
    """Look up a user by ID."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, role, user_tier, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        return cur.fetchone()


def insert_payment(user_id: int, amount_cents: int, currency: str,
                   status: str = "pending") -> int:
    """Insert a new payment record and return its ID."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO payments (user_id, amount_cents, currency, status)
               VALUES (%s, %s, %s, %s) RETURNING id""",
            (user_id, amount_cents, currency, status),
        )
        return cur.fetchone()["id"]


def update_payment_status(payment_id: int, status: str,
                          charge_id: str | None = None) -> None:
    """Update the status (and optionally charge_id) of a payment."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        if charge_id:
            cur.execute(
                "UPDATE payments SET status = %s, charge_id = %s WHERE id = %s",
                (status, charge_id, payment_id),
            )
        else:
            cur.execute(
                "UPDATE payments SET status = %s WHERE id = %s",
                (status, payment_id),
            )


def get_payment(payment_id: int) -> dict | None:
    """Retrieve a payment by its ID."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, user_id, amount_cents, currency, status, charge_id "
            "FROM payments WHERE id = %s",
            (payment_id,),
        )
        return cur.fetchone()


def list_user_payments(user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    """List payments for a given user, newest first."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            """SELECT id, amount_cents, currency, status, created_at
               FROM payments WHERE user_id = %s
               ORDER BY created_at DESC LIMIT %s OFFSET %s""",
            (user_id, limit, offset),
        )
        return cur.fetchall()
