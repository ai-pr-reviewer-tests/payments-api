"""Currency conversion endpoints."""

import logging

from flask import Blueprint, request, jsonify, g
from marshmallow import Schema, fields, validate, ValidationError

from src.auth.jwt_handler import require_auth
from src.payments.currency import (
    convert_amount,
    process_international_payment,
    get_conversion_metadata,
    SUPPORTED_CURRENCIES,
)
from src.payments.gateway import PaymentError

logger = logging.getLogger(__name__)

currency_bp = Blueprint("currency", __name__)


class ConvertSchema(Schema):
    amount_cents = fields.Int(required=True, validate=validate.Range(min=1))
    from_currency = fields.Str(required=True)
    to_currency = fields.Str(required=True)


class InternationalPaymentSchema(Schema):
    amount_cents = fields.Int(required=True, validate=validate.Range(min=1))
    source_currency = fields.Str(required=True)
    target_currency = fields.Str(required=True)
    source_token = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(load_default="")


@currency_bp.route("/convert", methods=["POST"])
@require_auth
def convert():
    """Preview a currency conversion without processing a payment."""
    try:
        schema = ConvertSchema()
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.messages}), 400

    try:
        result = convert_amount(
            data["amount_cents"], data["from_currency"], data["to_currency"],
        )
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


@currency_bp.route("/pay", methods=["POST"])
@require_auth
def international_payment():
    """Process an international payment with automatic currency conversion."""
    try:
        schema = InternationalPaymentSchema()
        data = schema.load(request.get_json(silent=True) or {})
    except ValidationError as e:
        return jsonify({"error": "Validation failed", "details": e.messages}), 400

    try:
        result = process_international_payment(
            user_id=g.current_user_id,
            amount_cents=data["amount_cents"],
            source_currency=data["source_currency"],
            target_currency=data["target_currency"],
            source_token=data["source_token"],
            description=data["description"],
        )
        return jsonify(result), 201
    except (PaymentError, ValueError) as e:
        return jsonify({"error": str(e)}), 400


@currency_bp.route("/supported", methods=["GET"])
def supported_currencies():
    """List all supported currencies."""
    return jsonify({"currencies": list(SUPPORTED_CURRENCIES)}), 200


@currency_bp.route("/conversion/<int:payment_id>", methods=["GET"])
@require_auth
def get_payment_conversion(payment_id: int):
    """Get conversion details for a specific payment."""
    metadata = get_conversion_metadata(payment_id)
    if metadata is None:
        return jsonify({"error": "No conversion data found for this payment"}), 404
    return jsonify(metadata), 200
