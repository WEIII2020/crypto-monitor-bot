import pytest
from src.config import Config


def test_config_loads_from_env(monkeypatch):
    """Test that Config loads values from environment variables"""
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'test_token_123')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', '987654321')
    monkeypatch.setenv('WARNING_THRESHOLD_5M', '12.5')

    config = Config()

    assert config.telegram_bot_token == 'test_token_123'
    assert config.telegram_chat_id == 987654321
    assert config.warning_threshold_5m == 12.5


def test_config_has_default_values(monkeypatch):
    """Test that Config provides sensible defaults"""
    monkeypatch.setenv('TELEGRAM_BOT_TOKEN', 'token')
    monkeypatch.setenv('TELEGRAM_CHAT_ID', '123')

    config = Config()

    assert config.log_level == 'INFO'
    assert config.enable_night_mode is False
    assert config.night_start_hour == 23


def test_config_raises_on_missing_required_fields(monkeypatch):
    """Test that Config raises error when required fields missing"""
    monkeypatch.delenv('TELEGRAM_BOT_TOKEN', raising=False)

    with pytest.raises(ValueError, match='TELEGRAM_BOT_TOKEN'):
        Config()
