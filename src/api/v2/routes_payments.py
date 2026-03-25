"""V2 Payment endpoints with enhanced features."""
from flask import Blueprint, request, jsonify, g
from marshmallow import ValidationError

from src.auth.jwt_handler import require_auth
from src.payments.providers.factory import get_provider
from src.payments.providers.base import ChargeStatus
from src.db.queries import get_payment, insert_payment, update_payment_status

payments_v2_bp = Blueprint("payments_v2", __name__)


@payments_v2_bp.route("/charge", methods=["POST"])
@require_auth
def create_charge_v2():
    """Create a charge with provider selection."""
    data = request.get_json(silent=True) or {}
    
    provider_name = data.get("provider", "stripe")
    amount_cents = data.get("amount_cents", 0)
    currency = data.get("currency", "usd")
    source_token = data.get("source_token", "")
    
    if amount_cents <= 0:
        return jsonify({"error": "Amount must be positive"}), 400
    
    provider = get_provider(provider_name)
    if not provider.supports_currency(currency):
        return jsonify({"error": f"Provider {provider_name} does not support {currency}"}), 400
    
    payment_id = insert_payment(g.current_user_id, amount_cents, currency)
    
    result = provider.create_charge(
        amount_cents=amount_cents,
        currency=currency,
        source_token=source_token,
        description=data.get("description", ""),
    )
    
    if result.status == ChargeStatus.SUCCEEDED:
        update_payment_status(payment_id, "completed", result.provider_charge_id)
    elif result.status == ChargeStatus.FAILED:
        update_payment_status(payment_id, "failed")
    
    return jsonify({
        "payment_id": payment_id,
        "provider": provider_name,
        "charge_id": result.provider_charge_id,
        "status": result.status.value,
        "amount": result.amount_cents,
        "currency": result.currency,
    }), 201
