"""Authentication endpoints."""

import bcrypt
from flask import Blueprint, request, jsonify

from src.auth.jwt_handler import create_token, require_auth
from src.auth.sessions import create_session, revoke_session
from src.db.queries import get_user_by_email
from src.api.validation import LoginSchema, validate_request_data

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate a user and return a JWT."""
    from marshmallow import ValidationError
    try:
        data = validate_request_data(LoginSchema, request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.messages}), 400

    user = get_user_by_email(data["email"])
    if user is None:
        return jsonify({"error": "Invalid credentials"}), 401

    if not bcrypt.checkpw(data["password"].encode(), user["password_hash"].encode()):
        return jsonify({"error": "Invalid credentials"}), 401

    token = create_token(user["id"], user["role"])
    create_session(user["id"], token)

    return jsonify({"token": token, "user_id": user["id"]}), 200


@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    """Invalidate the current session."""
    from flask import g
    revoke_session(g.current_user_id)
    return jsonify({"message": "Logged out"}), 200
