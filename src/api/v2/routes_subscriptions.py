"""V2 Subscription endpoints."""

from flask import Blueprint, request, jsonify, g

from src.auth.jwt_handler import require_auth
from src.payments.subscription import (
    create_subscription, cancel_subscription,
    renew_subscription, get_expiring_subscriptions,
)

subscriptions_bp = Blueprint("subscriptions", __name__)


@subscriptions_bp.route("/", methods=["POST"])
@require_auth
def create_sub():
    """Create a new subscription."""
    data = request.get_json(silent=True) or {}
    plan_id = data.get("plan_id")
    if not plan_id:
        return jsonify({"error": "plan_id is required"}), 400

    try:
        sub_id = create_subscription(g.current_user_id, plan_id)
        return jsonify({"subscription_id": sub_id}), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@subscriptions_bp.route("/<int:sub_id>/cancel", methods=["POST"])
@require_auth
def cancel_sub(sub_id: int):
    """Cancel a subscription."""
    cancel_subscription(sub_id)
    return jsonify({"message": "Subscription cancelled"}), 200


@subscriptions_bp.route("/<int:sub_id>/renew", methods=["POST"])
@require_auth
def renew_sub(sub_id: int):
    """Renew a subscription."""
    try:
        renew_subscription(sub_id)
        return jsonify({"message": "Subscription renewed"}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@subscriptions_bp.route("/expiring", methods=["GET"])
@require_auth
def list_expiring():
    """List subscriptions expiring soon."""
    days = request.args.get("days", 3, type=int)
    subs = get_expiring_subscriptions(days)
    return jsonify({"subscriptions": [dict(s) for s in subs]}), 200
