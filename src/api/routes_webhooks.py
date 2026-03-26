"""Webhook route handlers."""

import logging

from flask import Blueprint, request, jsonify

from src.webhooks.handler import verify_webhook_signature, handle_webhook_event

logger = logging.getLogger(__name__)

webhooks_bp = Blueprint("webhooks", __name__)


@webhooks_bp.route("/stripe", methods=["POST"])
def stripe_webhook():
    """Receive and process Stripe webhook events.

    This endpoint does not require JWT authentication — Stripe authenticates
    via its webhook signature header instead.
    """
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    if not sig_header:
        return jsonify({"error": "Missing Stripe-Signature header"}), 400

    try:
        event = verify_webhook_signature(payload, sig_header)
    except ValueError as e:
        logger.warning("Webhook rejected: %s", str(e))
        return jsonify({"error": str(e)}), 400

    result = handle_webhook_event(event)

    status_code = 200
    if result.get("status") == "failed":
        status_code = 500
        logger.error("Webhook processing failed for event %s", result.get("event_id"))

    return jsonify(result), status_code
