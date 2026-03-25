"""Webhook endpoints."""
from flask import Blueprint, request, jsonify
from src.payments.webhooks.handler import handle_webhook

webhooks_bp = Blueprint("webhooks", __name__)


@webhooks_bp.route("/stripe", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.get_data()
    signature = request.headers.get("Stripe-Signature", "")
    result = handle_webhook("stripe", payload, signature)
    return jsonify(result), 200


@webhooks_bp.route("/braintree", methods=["POST"])
def braintree_webhook():
    """Handle Braintree webhook events."""
    payload = request.get_data()
    signature = request.headers.get("X-Braintree-Signature", "")
    result = handle_webhook("braintree", payload, signature)
    return jsonify(result), 200
