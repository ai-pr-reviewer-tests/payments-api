"""Refund endpoints."""

from flask import Blueprint, request, jsonify, g
from marshmallow import Schema, fields, validate, ValidationError

from src.auth.jwt_handler import require_auth
from src.payments.refunds import process_refund, get_refund_history, REFUND_REASONS
from src.payments.gateway import PaymentError

refunds_bp = Blueprint("refunds", __name__)


class RefundRequestSchema(Schema):
    amount_cents = fields.Int(validate=validate.Range(min=1), load_default=None)
    reason = fields.Str(
        validate=validate.OneOf(REFUND_REASONS),
        load_default="customer_request",
    )


@refunds_bp.route("/<int:payment_id>/refund", methods=["POST"])
@require_auth
def create_refund(payment_id: int):
    """Process a refund for a specific payment."""
    try:
        schema = RefundRequestSchema()
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.messages}), 400

    try:
        result = process_refund(
            payment_id=payment_id,
            amount_cents=data["amount_cents"],
            reason=data["reason"],
            initiated_by=g.current_user_id,
        )
        return jsonify(result), 200
    except PaymentError as e:
        return jsonify({"error": str(e)}), 400


@refunds_bp.route("/<int:payment_id>/refunds", methods=["GET"])
@require_auth
def list_refunds(payment_id: int):
    """List all refunds for a payment."""
    try:
        history = get_refund_history(payment_id)
        return jsonify({
            "payment_id": payment_id,
            "refunds": history,
            "count": len(history),
        }), 200
    except PaymentError as e:
        return jsonify({"error": str(e)}), 400
