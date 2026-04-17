import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables"""

    def __init__(self):
        # Required fields
        self.telegram_bot_token = self._get_required('TELEGRAM_BOT_TOKEN')
        try:
            self.telegram_chat_id = int(self._get_required('TELEGRAM_CHAT_ID'))
        except ValueError as e:
            raise ValueError(f'TELEGRAM_CHAT_ID must be a valid integer: {e}')

        # Database
        self.database_url = os.getenv(
            'DATABASE_URL',
            'postgresql://cryptobot:password@localhost:5432/crypto_monitor'
        )
        self.redis_url = os.getenv(
            'REDIS_URL',
            'redis://:password@localhost:6379/0'
        )

        # Alert thresholds
        try:
            self.warning_threshold_5m = float(os.getenv('WARNING_THRESHOLD_5M', '10.0'))
        except ValueError as e:
            raise ValueError(f'WARNING_THRESHOLD_5M must be a valid number: {e}')

        try:
            self.critical_threshold_5m = float(os.getenv('CRITICAL_THRESHOLD_5M', '20.0'))
        except ValueError as e:
            raise ValueError(f'CRITICAL_THRESHOLD_5M must be a valid number: {e}')

        try:
            self.volume_warning_multiplier = float(os.getenv('VOLUME_WARNING_MULTIPLIER', '5.0'))
        except ValueError as e:
            raise ValueError(f'VOLUME_WARNING_MULTIPLIER must be a valid number: {e}')

        try:
            self.volume_critical_multiplier = float(os.getenv('VOLUME_CRITICAL_MULTIPLIER', '10.0'))
        except ValueError as e:
            raise ValueError(f'VOLUME_CRITICAL_MULTIPLIER must be a valid number: {e}')

        # Monitoring settings
        self.enable_night_mode = os.getenv('ENABLE_NIGHT_MODE', 'false').lower() == 'true'
        try:
            self.night_start_hour = int(os.getenv('NIGHT_START_HOUR', '23'))
        except ValueError as e:
            raise ValueError(f'NIGHT_START_HOUR must be a valid integer: {e}')

        try:
            self.night_end_hour = int(os.getenv('NIGHT_END_HOUR', '7'))
        except ValueError as e:
            raise ValueError(f'NIGHT_END_HOUR must be a valid integer: {e}')

        # Logging
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')

        # Exchange API keys (optional)
        self.binance_api_key = os.getenv('BINANCE_API_KEY')
        self.binance_api_secret = os.getenv('BINANCE_API_SECRET')

    def _get_required(self, key: str) -> str:
        """Get required environment variable or raise error"""
        value = os.getenv(key)
        if not value:
            raise ValueError(f'Required environment variable {key} is not set')
        return value


# Global config instance
try:
    config = Config()
except ValueError:
    # Allow import without configuration for testing
    config = None  # type: ignore
