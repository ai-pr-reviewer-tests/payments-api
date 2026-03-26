"""User search endpoints with pagination."""

import logging

from flask import Blueprint, request, jsonify, g
from marshmallow import Schema, fields, validate, ValidationError

from src.auth.jwt_handler import require_auth
from src.auth.permissions import require_role
from src.db.search import (
    search_users,
    get_user_details,
    search_users_by_payment_activity,
    SORTABLE_FIELDS,
    MAX_PAGE_SIZE,
)

logger = logging.getLogger(__name__)

search_bp = Blueprint("search", __name__)


class UserSearchSchema(Schema):
    q = fields.Str(load_default=None, validate=validate.Length(max=200))
    role = fields.Str(load_default=None, validate=validate.OneOf(["user", "admin", "support"]))
    sort_by = fields.Str(load_default="created_at")
    sort_dir = fields.Str(load_default="DESC")
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Int(load_default=25, validate=validate.Range(min=1, max=MAX_PAGE_SIZE))


class PaymentActivitySearchSchema(Schema):
    min_payments = fields.Int(load_default=1, validate=validate.Range(min=1))
    min_total_cents = fields.Int(load_default=None, validate=validate.Range(min=0))
    sort_by = fields.Str(load_default="total_spent")
    sort_dir = fields.Str(load_default="DESC")
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Int(load_default=25, validate=validate.Range(min=1, max=MAX_PAGE_SIZE))


@search_bp.route("/users", methods=["GET"])
@require_auth
@require_role("admin", "support")
def search_users_endpoint():
    """Search users with optional text query, role filter, and pagination."""
    try:
        schema = UserSearchSchema()
        params = schema.load(request.args.to_dict())
    except ValidationError as e:
        return jsonify({"error": "Invalid parameters", "details": e.messages}), 400

    result = search_users(
        query_text=params["q"],
        role=params["role"],
        sort_by=params["sort_by"],
        sort_dir=params["sort_dir"],
        page=params["page"],
        page_size=params["page_size"],
    )

    logger.info(
        "User search by %s: q=%s role=%s results=%d",
        g.current_user_id, params["q"], params["role"], result["total"],
    )

    return jsonify(result), 200


@search_bp.route("/users/<int:user_id>", methods=["GET"])
@require_auth
@require_role("admin", "support")
def get_user_detail(user_id: int):
    """Get detailed information about a specific user."""
    user = get_user_details(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user), 200


@search_bp.route("/users/by-activity", methods=["GET"])
@require_auth
@require_role("admin")
def search_by_payment_activity():
    """Search users by their payment activity metrics."""
    try:
        schema = PaymentActivitySearchSchema()
        params = schema.load(request.args.to_dict())
    except ValidationError as e:
        return jsonify({"error": "Invalid parameters", "details": e.messages}), 400

    result = search_users_by_payment_activity(
        min_payments=params["min_payments"],
        min_total_cents=params["min_total_cents"],
        sort_by=params["sort_by"],
        sort_dir=params["sort_dir"],
        page=params["page"],
        page_size=params["page_size"],
    )

    return jsonify(result), 200
