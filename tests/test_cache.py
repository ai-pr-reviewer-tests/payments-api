"""Tests for caching layer."""

import json
from unittest.mock import MagicMock, patch

from src.cache.cache_layer import cached, set_cached, invalidate, TTL_CONFIG


class TestCacheLayer:
    def test_cache_miss_returns_none(self, mock_redis):
        mock_redis.get.return_value = None
        result = cached("user_profile", "42")
        assert result is None

    def test_cache_hit(self, mock_redis):
        mock_redis.get.return_value = json.dumps({"email": "a@b.com"}).encode()
        result = cached("user_profile", "42")
        assert result["email"] == "a@b.com"

    def test_set_cached_uses_correct_ttl(self, mock_redis):
        set_cached("payment_details", "99", {"amount": 100})
        mock_redis.setex.assert_called_once()
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == TTL_CONFIG["payment_details"]

    def test_invalidate(self, mock_redis):
        invalidate("user_profile", "42")
        mock_redis.delete.assert_called_once_with("cache:user_profile:42")
