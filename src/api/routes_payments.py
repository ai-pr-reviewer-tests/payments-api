"""Payment endpoints."""

from flask import Blueprint, request, jsonify, g
from marshmallow import ValidationError

from src.auth.jwt_handler import require_auth
from src.api.validation import ChargeSchema, RefundSchema, validate_request
from src.payments.processor import process_charge, process_refund
from src.payments.gateway import PaymentError
from src.db.queries import get_payment, decrement_discount_uses
from src.payments.discounts import validate_discount_code, apply_discount

payments_bp = Blueprint("payments", __name__)


@payments_bp.route("/charge", methods=["POST"])
@require_auth
def create_charge():
    """Create a new payment charge."""
    try:
        data = validate_request(ChargeSchema, request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.messages}), 400

    amount_cents = data["amount_cents"]

    # Apply discount code if provided
    raw_body = request.get_json(silent=True) or {}
    discount_code = raw_body.get("discount_code")
    if discount_code:
        discount = validate_discount_code(discount_code)
        if discount is None:
            return jsonify({"error": "Invalid or expired discount code"}), 400
        amount_cents = apply_discount(amount_cents, discount)
        decrement_discount_uses(discount["id"])

    try:
        result = process_charge(
            user_id=g.current_user_id,
            amount_cents=amount_cents,
            currency=data["currency"],
            source_token=data["source_token"],
            description=data["description"],
        )
        return jsonify(result), 201
    except PaymentError as e:
        return jsonify({"error": str(e)}), 400


@payments_bp.route("/<int:payment_id>", methods=["GET"])
@require_auth
def get_payment_details(payment_id: int):
    """Retrieve details for a specific payment."""
    payment = get_payment(payment_id)
    if payment is None:
        return jsonify({"error": "Payment not found"}), 404

    # Users can only see their own payments; support/admin can see all
    if payment["user_id"] != g.current_user_id and g.current_user_role == "user":
        return jsonify({"error": "Payment not found"}), 404

    return jsonify(payment), 200


@payments_bp.route("/<int:payment_id>/refund", methods=["POST"])
@require_auth
def refund_payment(payment_id: int):
    """Refund a payment."""
    try:
        data = validate_request(RefundSchema, request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.messages}), 400

    try:
        result = process_refund(payment_id, data.get("amount_cents"))
        return jsonify(result), 200
    except PaymentError as e:
        return jsonify({"error": str(e)}), 400
