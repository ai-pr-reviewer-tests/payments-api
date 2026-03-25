"""V2 Webhook endpoints."""
from flask import Blueprint, request, jsonify
from src.payments.webhooks.handler import handle_webhook

webhooks_v2_bp = Blueprint("webhooks_v2", __name__)


@webhooks_v2_bp.route("/<provider>", methods=["POST"])
def webhook_handler(provider: str):
    """Generic webhook handler for any provider."""
    payload = request.get_data()
    sig_header = _get_signature_header(provider)
    signature = request.headers.get(sig_header, "")
    
    result = handle_webhook(provider, payload, signature)
    return jsonify(result), 200


def _get_signature_header(provider: str) -> str:
    """Get the signature header name for a provider."""
    headers = {
        "stripe": "Stripe-Signature",
        "braintree": "X-Braintree-Signature",
        "adyen": "X-Adyen-Hmac-Signature",
    }
    return headers.get(provider, "X-Webhook-Signature")
