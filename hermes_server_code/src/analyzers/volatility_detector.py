"""Simple volatility detector for MVP"""

from typing import Dict, Optional
from datetime import datetime

from src.database.redis_client import redis_client
from src.database.postgres import postgres_client
from src.utils.logger import logger
from src.config import config


class VolatilityDetector:
    """Detect significant price movements"""

    def __init__(self):
        self.warning_threshold = config.warning_threshold_5m
        self.critical_threshold = config.critical_threshold_5m

    async def check_volatility(self, exchange: str, symbol: str) -> Optional[Dict]:
        """Check if price change exceeds thresholds

        Returns alert dict if threshold exceeded, None otherwise
        """
        try:
            # Get last 5 minutes of prices from Redis
            prices = await redis_client.get_prices(exchange, symbol, minutes=5)

            if len(prices) < 2:
                return None

            # Calculate price change percentage
            latest_price = prices[0]['price']
            earliest_price = prices[-1]['price']

            if earliest_price == 0:
                return None

            change_percent = ((latest_price - earliest_price) / earliest_price) * 100

            # Determine alert level
            alert_level = None
            if abs(change_percent) >= self.critical_threshold:
                alert_level = 'CRITICAL'
            elif abs(change_percent) >= self.warning_threshold:
                alert_level = 'WARNING'

            if alert_level:
                # Check if alert already sent (deduplication)
                alert_key = f"{symbol}_PRICE_SPIKE"
                already_sent = await redis_client.check_alert_sent(symbol, 'PRICE_SPIKE')

                if already_sent:
                    logger.debug(f"Alert already sent for {symbol}, skipping")
                    return None

                # Mark as sent (5 minute cooldown)
                await redis_client.mark_alert_sent(symbol, 'PRICE_SPIKE', ttl_seconds=300)

                return {
                    'symbol': symbol,
                    'exchange': exchange,
                    'alert_type': 'PRICE_SPIKE',
                    'alert_level': alert_level,
                    'price': latest_price,
                    'change_percent': round(change_percent, 2),
                    'message': f"{'🚨' if alert_level == 'CRITICAL' else '⚠️'} {symbol} {'+' if change_percent > 0 else ''}{change_percent:.2f}% in 5 min"
                }

            return None

        except Exception as e:
            logger.error(f"Error checking volatility for {symbol}: {e}")
            return None
