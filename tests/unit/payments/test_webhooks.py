"""Tests for webhook handling."""
import json
import pytest
from unittest.mock import patch, MagicMock

from src.payments.webhooks.handler import handle_webhook, EVENT_HANDLERS


class TestWebhookHandler:
    @patch("src.payments.webhooks.handler.get_provider")
    def test_invalid_signature_rejected(self, mock_provider):
        provider = MagicMock()
        provider.validate_webhook.return_value = False
        mock_provider.return_value = provider
        
        result = handle_webhook("stripe", b"payload", "bad-sig")
        assert result["status"] == "invalid_signature"

    @patch("src.payments.webhooks.handler.get_provider")
    def test_valid_event_processed(self, mock_provider):
        provider = MagicMock()
        provider.validate_webhook.return_value = True
        mock_provider.return_value = provider
        
        event = {"type": "charge.succeeded", "data": {"object": {"id": "ch_test"}}}
        result = handle_webhook("stripe", json.dumps(event).encode(), "valid-sig")
        assert result["status"] == "processed"

    @patch("src.payments.webhooks.handler.get_provider")
    def test_unknown_event_ignored(self, mock_provider):
        provider = MagicMock()
        provider.validate_webhook.return_value = True
        mock_provider.return_value = provider
        
        event = {"type": "unknown.event", "data": {}}
        result = handle_webhook("stripe", json.dumps(event).encode(), "valid-sig")
        assert result["status"] == "ignored"
