"""Tests for session management."""
from unittest.mock import patch, MagicMock
from src.auth.sessions import create_session, get_session, revoke_session


class TestSessions:
    @patch("src.auth.sessions.get_redis")
    def test_create_session(self, mock_get_redis):
        mock_r = MagicMock()
        mock_get_redis.return_value = mock_r
        create_session(1, "token123")
        mock_r.setex.assert_called_once()

    @patch("src.auth.sessions.get_redis")
    def test_get_session_hit(self, mock_get_redis):
        mock_r = MagicMock()
        mock_r.get.return_value = b"token123"
        mock_get_redis.return_value = mock_r
        assert get_session(1) == "token123"

    @patch("src.auth.sessions.get_redis")
    def test_get_session_miss(self, mock_get_redis):
        mock_r = MagicMock()
        mock_r.get.return_value = None
        mock_get_redis.return_value = mock_r
        assert get_session(1) is None

    @patch("src.auth.sessions.get_redis")
    def test_revoke_session(self, mock_get_redis):
        mock_r = MagicMock()
        mock_get_redis.return_value = mock_r
        revoke_session(1)
        mock_r.delete.assert_called_once()
