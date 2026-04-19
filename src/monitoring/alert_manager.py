"""
告警管理模块

管理系统告警，支持多种告警渠道
"""

import asyncio
from typing import Dict, Optional
from datetime import datetime
from telegram import Bot

from src.utils.logger import logger


class AlertManager:
    """告警管理器"""

    def __init__(self, telegram_bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        初始化告警管理器

        Args:
            telegram_bot_token: Telegram Bot Token
            chat_id: Telegram Chat ID
        """
        self.telegram_bot_token = telegram_bot_token
        self.chat_id = chat_id
        self.bot: Optional[Bot] = None

        # 告警级别图标
        self.status_icons = {
            'healthy': '✅',
            'warning': '⚠️',
            'critical': '🚨',
            'unknown': '❓'
        }

    async def initialize(self):
        """初始化告警渠道"""
        if self.telegram_bot_token:
            try:
                self.bot = Bot(token=self.telegram_bot_token)
                logger.info("Telegram alert channel initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Telegram bot: {e}")

    async def send_alert(self, alert: Dict):
        """
        发送告警

        Args:
            alert: 告警信息
        """
        # 构建告警消息
        status = alert.get('status', 'unknown')
        icon = self.status_icons.get(status, '📢')

        message = f"""
{icon} **系统告警**

📋 检查项: {alert.get('check_name', 'Unknown')}
📊 状态: {status.upper()}
💬 消息: {alert.get('message', 'No message')}

🕐 时间: {alert.get('timestamp', 'Unknown')}
"""

        # 添加详细信息
        details = alert.get('details', {})
        if details:
            message += "\n📝 详细信息:\n"
            for key, value in details.items():
                if isinstance(value, (int, float)):
                    message += f"  • {key}: {value:.2f}\n"
                else:
                    message += f"  • {key}: {value}\n"

        # 发送到 Telegram
        if self.bot and self.chat_id:
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
                logger.info(f"Alert sent: {alert.get('check_name')} - {status}")
            except Exception as e:
                logger.error(f"Failed to send Telegram alert: {e}")

        # 可以在这里添加其他告警渠道（邮件、Slack 等）

    async def send_recovery(self, check_name: str, message: str):
        """
        发送恢复通知

        Args:
            check_name: 检查项名称
            message: 恢复消息
        """
        recovery_message = f"""
✅ **系统恢复**

📋 检查项: {check_name}
💬 消息: {message}

🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        if self.bot and self.chat_id:
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=recovery_message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send recovery notification: {e}")

    async def send_startup_notification(self):
        """发送启动通知"""
        message = """
🚀 **系统启动**

Crypto Monitor Bot 已启动
健康监控已激活

使用 /status 查看系统状态
"""

        if self.bot and self.chat_id:
            try:
                await self.bot.send_message(
                    chat_id=self.chat_id,
                    text=message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to send startup notification: {e}")

    async def close(self):
        """关闭告警管理器"""
        # Telegram Bot 会自动关闭
        pass
