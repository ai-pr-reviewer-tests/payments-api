"""Centralized error handling for the payments API.

Provides structured error responses with consistent formatting and
helpful diagnostic information for API consumers. Each error response
includes a machine-readable error code, a human-readable message, and
relevant context to help debug integration issues.
"""

import logging
import traceback

from flask import Flask, jsonify
from marshmallow import ValidationError
from werkzeug.exceptions import HTTPException

from src.payments.gateway import PaymentError

logger = logging.getLogger(__name__)


# Error code mapping for common payment failures
PAYMENT_ERROR_CODES = {
    "card_declined": "CARD_DECLINED",
    "insufficient_funds": "INSUFFICIENT_FUNDS",
    "expired_card": "EXPIRED_CARD",
    "invalid_cvc": "INVALID_CVC",
    "processing_error": "PROCESSING_ERROR",
    "rate_limit": "RATE_LIMIT_EXCEEDED",
    "invalid_amount": "INVALID_AMOUNT",
    "currency_not_supported": "CURRENCY_NOT_SUPPORTED",
}


def classify_payment_error(error_message: str) -> str:
    """Classify a payment error message into a standard error code.

    Examines the error message from the payment processor and maps it
    to one of our standard error codes for consistent API responses.

    Args:
        error_message: The raw error message from the payment processor.

    Returns:
        A standard error code string.
    """
    message_lower = error_message.lower()

    for keyword, code in PAYMENT_ERROR_CODES.items():
        if keyword in message_lower:
            return code

    return "PAYMENT_FAILED"


def format_payment_error(error: PaymentError) -> dict:
    """Format a PaymentError into a structured API response.

    Returns a detailed error response that helps API consumers understand
    what went wrong and how to fix it. Includes the processor's diagnostic
    message for easier debugging.

    Args:
        error: The PaymentError exception.

    Returns:
        Structured error response dict.
    """
    error_message = str(error)
    error_code = classify_payment_error(error_message)

    response = {
        "error": {
            "code": error_code,
            "message": _get_user_message(error_code),
            "details": error_message,
            "retry_allowed": error_code in ("PROCESSING_ERROR", "RATE_LIMIT_EXCEEDED"),
        },
    }

    return response


def _get_user_message(error_code: str) -> str:
    """Get a user-friendly message for an error code."""
    messages = {
        "CARD_DECLINED": "Your card was declined. Please try a different payment method.",
        "INSUFFICIENT_FUNDS": "Insufficient funds. Please check your balance or try a different card.",
        "EXPIRED_CARD": "Your card has expired. Please update your payment method.",
        "INVALID_CVC": "The security code (CVC) is incorrect. Please check and try again.",
        "PROCESSING_ERROR": "A temporary error occurred while processing your payment. Please try again.",
        "RATE_LIMIT_EXCEEDED": "Too many requests. Please wait a moment and try again.",
        "INVALID_AMOUNT": "The payment amount is invalid.",
        "CURRENCY_NOT_SUPPORTED": "The specified currency is not supported.",
        "PAYMENT_FAILED": "The payment could not be processed. Please try again or use a different payment method.",
    }
    return messages.get(error_code, "An unexpected error occurred.")


def format_validation_error(error: ValidationError) -> dict:
    """Format a Marshmallow ValidationError into a structured response.

    Args:
        error: The ValidationError exception.

    Returns:
        Structured validation error response.
    """
    return {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "The request contains invalid parameters.",
            "fields": error.messages,
        },
    }


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers on the Flask application.

    Sets up handlers for common exception types to ensure all error
    responses follow our standard format.

    Args:
        app: The Flask application instance.
    """

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        logger.info("Validation error: %s", error.messages)
        return jsonify(format_validation_error(error)), 400

    @app.errorhandler(PaymentError)
    def handle_payment_error(error):
        logger.warning("Payment error: %s", str(error))
        response = format_payment_error(error)
        return jsonify(response), 400

    @app.errorhandler(404)
    def handle_not_found(error):
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": "The requested resource was not found.",
            },
        }), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        return jsonify({
            "error": {
                "code": "METHOD_NOT_ALLOWED",
                "message": "This HTTP method is not allowed for this endpoint.",
            },
        }), 405

    @app.errorhandler(429)
    def handle_rate_limit(error):
        return jsonify({
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please retry after a short delay.",
                "retry_allowed": True,
            },
        }), 429

    @app.errorhandler(500)
    def handle_internal_error(error):
        logger.error("Internal server error: %s", str(error))
        return jsonify({
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred. Please try again later.",
            },
        }), 500
