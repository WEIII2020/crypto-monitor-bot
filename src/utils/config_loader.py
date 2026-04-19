"""
Config Loader - 配置文件加载器

功能：
- 加载 YAML 配置文件
- 环境变量覆盖
- 配置验证
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from src.utils.logger import logger


class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Args:
            config_path: 配置文件路径（默认为 config/config.yaml）
        """
        if config_path is None:
            # 默认路径：项目根目录/config/config.yaml
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "config.yaml"

        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}

        self._load_config()
        self._override_from_env()

    def _load_config(self):
        """加载 YAML 配置文件"""
        try:
            if not self.config_path.exists():
                logger.warning(f"配置文件不存在: {self.config_path}，使用默认配置")
                self.config = self._get_default_config()
                return

            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f) or {}

            logger.info(f"✅ 配置文件已加载: {self.config_path}")

        except Exception as e:
            logger.error(f"❌ 加载配置文件失败: {e}")
            self.config = self._get_default_config()

    def _override_from_env(self):
        """从环境变量覆盖配置"""
        # Telegram
        if telegram_token := os.getenv('TELEGRAM_BOT_TOKEN'):
            self.config.setdefault('telegram', {})['bot_token'] = telegram_token

        if telegram_chat_id := os.getenv('TELEGRAM_CHAT_ID'):
            self.config.setdefault('telegram', {})['chat_id'] = telegram_chat_id

        # Binance
        if binance_key := os.getenv('BINANCE_API_KEY'):
            self.config.setdefault('trading', {}).setdefault('binance', {})['api_key'] = binance_key

        if binance_secret := os.getenv('BINANCE_API_SECRET'):
            self.config.setdefault('trading', {}).setdefault('binance', {})['api_secret'] = binance_secret

        # Database
        if db_password := os.getenv('POSTGRES_PASSWORD'):
            self.config.setdefault('database', {}).setdefault('postgres', {})['password'] = db_password

        if redis_host := os.getenv('REDIS_HOST'):
            self.config.setdefault('database', {}).setdefault('redis', {})['host'] = redis_host

    def _get_default_config(self) -> Dict[str, Any]:
        """默认配置"""
        return {
            'monitoring': {
                'symbols_count': 200,
                'test_mode': False
            },
            'api': {
                'max_concurrent': 8,
                'base_delay': 0.1
            },
            'trading': {
                'enabled': False,
                'mode': 'simulation'
            },
            'telegram': {
                'enabled': True
            },
            'performance': {
                'stats_interval': 60,
                'log_level': 'INFO'
            },
            'mode': 'signal'
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值（支持点号路径）

        Args:
            key: 配置键（支持 'a.b.c' 格式）
            default: 默认值

        Returns:
            配置值

        Example:
            >>> config.get('trading.lana_rules.max_loss_usdt')
            200
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        获取整个配置段

        Args:
            section: 配置段名称

        Returns:
            配置段字典
        """
        return self.config.get(section, {})

    def set(self, key: str, value: Any):
        """
        设置配置值（支持点号路径）

        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def validate(self) -> bool:
        """
        验证配置完整性

        Returns:
            True if 配置有效
        """
        required_keys = [
            'monitoring',
            'api',
            'strategies',
            'telegram'
        ]

        for key in required_keys:
            if key not in self.config:
                logger.error(f"❌ 缺少必需配置段: {key}")
                return False

        # 验证交易配置（如果启用）
        if self.get('trading.enabled', False):
            if not self.get('trading.binance.api_key'):
                logger.error("❌ 交易已启用但缺少 Binance API Key")
                return False

        # 验证 Telegram 配置（如果启用）
        if self.get('telegram.enabled', True):
            if not self.get('telegram.bot_token'):
                logger.warning("⚠️ Telegram 已启用但缺少 bot_token")

        return True


# 全局配置实例
config = ConfigLoader()


if __name__ == "__main__":
    # 测试
    print("=== 配置加载测试 ===")
    print(f"监控币种数: {config.get('monitoring.symbols_count')}")
    print(f"交易已启用: {config.get('trading.enabled')}")
    print(f"运行模式: {config.get('mode')}")
    print(f"配置验证: {'✅ 通过' if config.validate() else '❌ 失败'}")
