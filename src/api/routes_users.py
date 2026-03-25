"""User profile endpoints."""

from flask import Blueprint, jsonify, g

from src.auth.jwt_handler import require_auth
from src.db.queries import get_user_by_id

users_bp = Blueprint("users", __name__)


@users_bp.route("/me", methods=["GET"])
@require_auth
def get_current_user():
    """Return the authenticated user's profile."""
    user = get_user_by_id(g.current_user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
    }), 200
