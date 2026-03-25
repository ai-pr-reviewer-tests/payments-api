"""Webhook event handler."""
import logging
from src.payments.providers.factory import get_provider
from src.db.queries import update_payment_status

logger = logging.getLogger(__name__)


EVENT_HANDLERS = {}


def register_handler(event_type: str):
    """Decorator to register a webhook event handler."""
    def decorator(f):
        EVENT_HANDLERS[event_type] = f
        return f
    return decorator


def handle_webhook(provider_name: str, payload: bytes, signature: str) -> dict:
    """Process an incoming webhook event."""
    provider = get_provider(provider_name)
    
    if not provider.validate_webhook(payload, signature):
        logger.warning("Invalid webhook signature for %s", provider_name)
        return {"status": "invalid_signature"}
    
    # Parse and dispatch event
    import json
    event = json.loads(payload)
    event_type = event.get("type", "")
    
    handler = EVENT_HANDLERS.get(event_type)
    if handler:
        handler(event)
        return {"status": "processed"}
    
    logger.info("Unhandled webhook event: %s", event_type)
    return {"status": "ignored"}


@register_handler("charge.succeeded")
def handle_charge_succeeded(event: dict) -> None:
    charge_id = event["data"]["object"]["id"]
    logger.info("Charge succeeded: %s", charge_id)


@register_handler("charge.failed")
def handle_charge_failed(event: dict) -> None:
    charge_id = event["data"]["object"]["id"]
    logger.warning("Charge failed: %s", charge_id)


@register_handler("refund.created")
def handle_refund_created(event: dict) -> None:
    refund_id = event["data"]["object"]["id"]
    logger.info("Refund created: %s", refund_id)
