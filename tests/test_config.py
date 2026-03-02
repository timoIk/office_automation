"""Tests for configuration."""

from src.common.config import Settings


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-tok")
    monkeypatch.setenv("ALLOWED_USER_IDS", "111,222,333")
    s = Settings()
    assert s.telegram_bot_token == "test-tok"
    assert s.allowed_user_id_list == [111, 222, 333]


def test_empty_allowed_users(monkeypatch):
    monkeypatch.setenv("ALLOWED_USER_IDS", "")
    s = Settings()
    assert s.allowed_user_id_list == []
