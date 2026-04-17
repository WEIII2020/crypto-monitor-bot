"""
Whale/Market Maker Behavior Detector
Detects accumulation (吸筹) and distribution (出货) signals
"""

from typing import Dict, Optional
from datetime import datetime

from src.database.redis_client import redis_client
from src.utils.logger import logger


class WhaleDetector:
    """Detect whale accumulation and distribution patterns"""

    def __init__(self):
        # Volume thresholds (multiplier of average volume)
        self.volume_spike_threshold = 5.0      # 5x average
        self.volume_low_threshold = 2.0        # 2x average

        # Price change thresholds
        self.sideways_threshold = 3.0          # ±3% considered sideways
        self.significant_rise = 10.0           # 10% rise
        self.moderate_rise = 8.0               # 8% rise
        self.significant_drop = 10.0           # 10% drop

    async def check_whale_activity(self, exchange: str, symbol: str) -> Optional[Dict]:
        """
        Check for whale accumulation/distribution patterns

        Returns alert dict if pattern detected, None otherwise
        """
        try:
            # Get last 5 minutes of prices
            recent_prices = await redis_client.get_prices(exchange, symbol, minutes=5)
            if len(recent_prices) < 2:
                return None

            # Get average volume for comparison (last 1 hour)
            avg_volume = await redis_client.get_avg_volume(exchange, symbol, minutes=60)
            if avg_volume == 0:
                return None

            # Calculate current metrics
            latest_price = recent_prices[0]['price']
            earliest_price = recent_prices[-1]['price']
            current_volume = recent_prices[0]['volume']

            if earliest_price == 0:
                return None

            # Price change percentage
            price_change_pct = ((latest_price - earliest_price) / earliest_price) * 100

            # Volume multiplier
            volume_multiplier = current_volume / avg_volume if avg_volume > 0 else 0

            # Pattern detection
            pattern = self._detect_pattern(price_change_pct, volume_multiplier)

            if pattern:
                # Check deduplication
                alert_key = f"{symbol}_WHALE_{pattern['type']}"
                already_sent = await redis_client.check_alert_sent(symbol, f"WHALE_{pattern['type']}")

                if already_sent:
                    logger.debug(f"Whale alert already sent for {symbol}, skipping")
                    return None

                # Mark as sent (10 minute cooldown for whale alerts)
                await redis_client.mark_alert_sent(symbol, f"WHALE_{pattern['type']}", ttl_seconds=600)

                return {
                    'symbol': symbol,
                    'exchange': exchange,
                    'alert_type': 'WHALE_ACTIVITY',
                    'alert_level': pattern['level'],
                    'pattern': pattern['type'],
                    'price': latest_price,
                    'change_percent': round(price_change_pct, 2),
                    'volume_multiplier': round(volume_multiplier, 1),
                    'message': self._format_message(symbol, pattern, price_change_pct, volume_multiplier, latest_price)
                }

            return None

        except Exception as e:
            logger.error(f"Error checking whale activity for {symbol}: {e}")
            return None

    def _detect_pattern(self, price_change_pct: float, volume_multiplier: float) -> Optional[Dict]:
        """
        Detect whale behavior patterns based on price and volume

        Returns pattern dict or None
        """
        abs_price_change = abs(price_change_pct)

        # 🟢 Pattern 1: Accumulation (吸筹)
        # Price sideways/down + High volume = Whale buying without pumping price
        if abs_price_change < self.sideways_threshold and volume_multiplier >= self.volume_spike_threshold:
            return {
                'type': 'ACCUMULATION',
                'level': 'WARNING',
                'description': '放量不涨，疑似吸筹'
            }

        # 🔴 Pattern 2: Distribution (出货)
        # Price spike up + High volume = Whale selling into pump
        if price_change_pct >= self.significant_rise and volume_multiplier >= self.volume_spike_threshold:
            return {
                'type': 'DISTRIBUTION',
                'level': 'CRITICAL',
                'description': '放量拉升，疑似出货'
            }

        # ⚠️ Pattern 3: Fake Breakout (假突破)
        # Price up but low volume = Weak rally, likely to fail
        if price_change_pct >= self.moderate_rise and volume_multiplier < self.volume_low_threshold:
            return {
                'type': 'FAKE_BREAKOUT',
                'level': 'WARNING',
                'description': '缩量上涨，警惕假突破'
            }

        # 💀 Pattern 4: Panic Selling (恐慌出逃)
        # Price dump + High volume = Mass panic
        if price_change_pct <= -self.significant_drop and volume_multiplier >= self.volume_spike_threshold:
            return {
                'type': 'PANIC_SELL',
                'level': 'CRITICAL',
                'description': '放量下跌，恐慌出逃'
            }

        # 📊 Pattern 5: Volume Spike (异常放量)
        # Extreme volume without clear price direction
        if volume_multiplier >= 10.0 and abs_price_change < self.significant_rise:
            return {
                'type': 'VOLUME_SPIKE',
                'level': 'WARNING',
                'description': '异常放量，可能对敲'
            }

        return None

    def _format_message(
        self,
        symbol: str,
        pattern: Dict,
        price_change: float,
        volume_mult: float,
        price: float
    ) -> str:
        """Format alert message with emoji and details"""

        emoji_map = {
            'ACCUMULATION': '🟢',
            'DISTRIBUTION': '🔴',
            'FAKE_BREAKOUT': '⚠️',
            'PANIC_SELL': '💀',
            'VOLUME_SPIKE': '📊'
        }

        emoji = emoji_map.get(pattern['type'], '🐋')

        message = f"{emoji} {pattern['description']}\n"
        message += f"📈 {symbol}\n"
        message += f"💰 价格: ${price:,.2f}\n"
        message += f"📊 涨跌: {'+' if price_change >= 0 else ''}{price_change:.2f}%\n"
        message += f"🔊 交易量: {volume_mult:.1f}x 平均值"

        return message
