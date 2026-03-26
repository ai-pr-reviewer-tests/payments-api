"""User profile endpoints."""

from flask import Blueprint, jsonify, request, g

from src.auth.jwt_handler import require_auth
from src.auth.permissions import require_role, Role
from src.db.queries import get_user_by_id, update_user_role

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


@users_bp.route("/<int:user_id>/role", methods=["PUT"])
@require_auth
def update_role(user_id: int):
    """Update a user's role. Requires admin privileges."""
    data = request.get_json(silent=True) or {}
    new_role = data.get("role")

    if new_role not in ("user", "support", "admin"):
        return jsonify({"error": "Invalid role"}), 400

    user = get_user_by_id(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    update_user_role(user_id, new_role)
    return jsonify({"message": f"Role updated to {new_role}", "user_id": user_id}), 200
