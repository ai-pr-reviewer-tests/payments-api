"""V2 Users API with filtering and search capabilities."""

from flask import Blueprint, jsonify, request, g

from src.auth.jwt_handler import require_auth
from src.auth.permissions import require_role, Role
from src.db.connection import get_db_connection

users_v2_bp = Blueprint("users_v2", __name__)


@users_v2_bp.route("/", methods=["GET"])
@require_auth
@require_role(Role.SUPPORT)
def list_users():
    """List users with optional filtering.

    Query parameters:
        role: Filter by role (user, support, admin)
        email: Filter by email (partial match)
        sort: Sort field (email, created_at)
        limit: Max results (default 50)
        offset: Pagination offset (default 0)
    """
    role_filter = request.args.get("role", "")
    email_filter = request.args.get("email", "")
    sort_field = request.args.get("sort", "created_at")
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    conn = get_db_connection()
    with conn.cursor() as cur:
        # Build query dynamically
        query = "SELECT id, email, role, created_at FROM users WHERE 1=1"
        params = []

        if role_filter:
            query += " AND role = %s"
            params.append(role_filter)

        if email_filter:
            # BUG: SQL injection — email_filter is concatenated directly
            # instead of using parameterized query
            query += f" AND email LIKE '%{email_filter}%'"

        # BUG: sort_field is user-controlled and injected directly into SQL
        if sort_field in ("email", "created_at", "role"):
            query += f" ORDER BY {sort_field} DESC"
        else:
            query += " ORDER BY created_at DESC"

        query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        cur.execute(query, params)
        users = cur.fetchall()

    # BUG: Exposes internal database IDs directly
    return jsonify({
        "users": [dict(u) for u in users],
        "count": len(users),
        "limit": limit,
        "offset": offset,
    }), 200


@users_v2_bp.route("/<int:user_id>", methods=["GET"])
@require_auth
@require_role(Role.SUPPORT)
def get_user_detail(user_id: int):
    """Get detailed user info including payment summary."""
    conn = get_db_connection()
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, email, role, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        user = cur.fetchone()

    if user is None:
        return jsonify({"error": "User not found"}), 404

    # Get payment summary
    with conn.cursor() as cur:
        cur.execute(
            """SELECT COUNT(*) as total_payments,
                      COALESCE(SUM(amount_cents), 0) as total_amount
               FROM payments WHERE user_id = %s AND status = 'completed'""",
            (user_id,),
        )
        summary = cur.fetchone()

    return jsonify({
        "user": dict(user),
        "payment_summary": {
            "total_payments": summary["total_payments"],
            "total_amount_cents": summary["total_amount"],
        },
    }), 200
