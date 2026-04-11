"""Telegram notification client for MVP"""

import asyncio
from typing import Dict
from telegram import Bot
from telegram.error import TelegramError

from src.config import config
from src.utils.logger import logger
from src.database.postgres import postgres_client


class TelegramNotifier:
    """Send alerts via Telegram"""

    def __init__(self):
        self.bot = Bot(token=config.telegram_bot_token)
        self.chat_id = config.telegram_chat_id

    async def send_alert(self, alert_data: Dict):
        """Send alert message to Telegram"""
        try:
            # Format message
            message = self._format_message(alert_data)

            # Send to Telegram
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )

            # Save to database
            symbol_record = await postgres_client.get_symbol(
                alert_data['symbol'],
                alert_data['exchange']
            )

            if symbol_record:
                await postgres_client.insert_alert({
                    'symbol_id': symbol_record['id'],
                    'exchange': alert_data['exchange'],
                    'alert_type': alert_data['alert_type'],
                    'alert_level': alert_data['alert_level'],
                    'price': alert_data['price'],
                    'change_percent': alert_data['change_percent'],
                    'message': alert_data['message']
                })

            logger.info(f"Alert sent: {alert_data['symbol']} {alert_data['change_percent']}%")

        except TelegramError as e:
            logger.error(f"Telegram error: {e}")
        except Exception as e:
            logger.error(f"Error sending alert: {e}")

    def _format_message(self, alert_data: Dict) -> str:
        """Format alert message"""
        level_emoji = '🚨' if alert_data['alert_level'] == 'CRITICAL' else '⚠️'
        direction = '📈' if alert_data['change_percent'] > 0 else '📉'

        message = f"""
{level_emoji} <b>{alert_data['alert_level']} ALERT</b>

{direction} <b>{alert_data['symbol']}</b> on {alert_data['exchange'].upper()}

💰 Current Price: ${alert_data['price']:.2f}
📊 Change: <b>{alert_data['change_percent']:+.2f}%</b> (5 min)

⏰ Time: {asyncio.get_event_loop().time()}
"""
        return message.strip()
