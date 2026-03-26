"""Webhook endpoints for receiving payment events from Stripe."""

import os
import logging

from flask import Blueprint, request, jsonify

from src.webhooks.signature import verify_signature
from src.webhooks.handler import process_event, WebhookProcessingError

logger = logging.getLogger(__name__)

webhooks_bp = Blueprint("webhooks", __name__)

WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")


@webhooks_bp.route("/stripe", methods=["POST"])
def stripe_webhook():
    """Receive and process Stripe webhook events.

    Verifies the signature, parses the event, and dispatches to the
    appropriate handler based on event type.
    """
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    if not WEBHOOK_SECRET:
        logger.error("Webhook secret not configured")
        return jsonify({"error": "Webhook processing unavailable"}), 503

    result = verify_signature(payload, sig_header, WEBHOOK_SECRET)
    if not result.valid:
        logger.warning("Webhook signature verification failed: %s", result.error)
        return jsonify({"error": "Invalid signature"}), 401

    try:
        event = request.get_json(force=True)
    except Exception:
        logger.error("Failed to parse webhook payload as JSON")
        return jsonify({"error": "Invalid payload"}), 400

    event_type = event.get("type")
    event_data = event.get("data", {}).get("object", {})

    if not event_type:
        return jsonify({"error": "Missing event type"}), 400

    try:
        processing_result = process_event(event_type, event_data)
        return jsonify(processing_result), 200
    except WebhookProcessingError as e:
        logger.error("Webhook processing error: %s", str(e))
        return jsonify({"error": "Processing failed"}), 500
