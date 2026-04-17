"""
OI (Open Interest) Monitor - 持仓量监控
基于 lana 的方法：检测 48h 内 OI 变动大但价格未反应的标的
"""

import aiohttp
from typing import Dict, Optional, List
from datetime import datetime, timedelta

from src.database.redis_client import redis_client
from src.utils.logger import logger


class OIMonitor:
    """
    持仓量监控器

    核心逻辑（lana方法）：
    - 48小时内 OI 变动 > 50%
    - 但价格变动 < 5%
    - 说明：资金提前埋伏，价格还未反应
    """

    def __init__(self):
        self.binance_futures_api = "https://fapi.binance.com/fapi/v1"

        # lana的阈值
        self.oi_spike_threshold = 0.5      # OI变动 >50%
        self.price_no_move_threshold = 0.05  # 价格变动 <5%
        self.alert_cooldown_seconds = 3600   # 1小时冷却

    async def check_oi_spike(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[Dict]:
        """
        检测OI异常（lana的核心信号之一）

        Returns:
            alert dict if OI spike detected, None otherwise
        """
        try:
            # 1. 获取当前OI
            current_oi = await self._get_current_oi(symbol)
            if not current_oi:
                return None

            # 2. 获取48小时前的OI（从Redis缓存）
            oi_48h_ago = await self._get_historical_oi(symbol, hours=48)
            if not oi_48h_ago:
                # 第一次检测，缓存当前OI
                await self._cache_oi(symbol, current_oi)
                return None

            # 3. 计算OI变化
            oi_change_pct = ((current_oi - oi_48h_ago) / oi_48h_ago) * 100

            # 4. 检查是否达到阈值（>50%）
            if abs(oi_change_pct) < self.oi_spike_threshold * 100:
                # 更新缓存
                await self._cache_oi(symbol, current_oi)
                return None

            # 5. 获取价格变化（48小时）
            prices_48h = await redis_client.get_prices(
                exchange,
                symbol,
                minutes=48 * 60
            )

            if len(prices_48h) < 10:
                return None

            latest_price = prices_48h[0]['price']
            price_48h_ago = prices_48h[-1]['price']

            if price_48h_ago == 0:
                return None

            price_change_pct = ((latest_price - price_48h_ago) / price_48h_ago) * 100

            # 6. lana的关键判断：OI变动大，但价格未动
            if abs(price_change_pct) > self.price_no_move_threshold * 100:
                # 价格已经反应了，不是好信号
                await self._cache_oi(symbol, current_oi)
                return None

            # 7. 检测到信号！
            logger.info(
                f"🎯 OI异常: {symbol} | "
                f"OI变动{oi_change_pct:+.1f}% | "
                f"价格仅{price_change_pct:+.1f}%"
            )

            # 8. 去重检查
            alert_key = f"OI_SPIKE_{symbol}"
            already_sent = await redis_client.check_alert_sent(symbol, alert_key)

            if already_sent:
                return None

            # 标记已发送（1小时冷却）
            await redis_client.mark_alert_sent(
                symbol,
                alert_key,
                ttl_seconds=self.alert_cooldown_seconds
            )

            # 更新缓存
            await self._cache_oi(symbol, current_oi)

            # 9. 返回信号
            return {
                'symbol': symbol,
                'exchange': exchange,
                'alert_type': 'OI_SPIKE',
                'alert_level': 'CRITICAL',
                'oi_change_pct': round(oi_change_pct, 2),
                'price_change_pct': round(price_change_pct, 2),
                'current_oi': current_oi,
                'oi_48h_ago': oi_48h_ago,
                'current_price': latest_price,
                'score': 40,  # 信号评分（用于融合）
                'message': self._format_message(
                    symbol,
                    oi_change_pct,
                    price_change_pct,
                    current_oi,
                    latest_price
                )
            }

        except Exception as e:
            logger.error(f"Error checking OI spike for {symbol}: {e}")
            return None

    async def _get_current_oi(self, symbol: str) -> Optional[float]:
        """
        获取当前持仓量（Open Interest）

        使用 Binance Futures API
        """
        try:
            # 转换符号格式：BTC/USDT -> BTCUSDT
            binance_symbol = symbol.replace('/', '')

            url = f"{self.binance_futures_api}/openInterest"
            params = {'symbol': binance_symbol}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status != 200:
                        logger.debug(f"Failed to fetch OI for {symbol}: HTTP {response.status}")
                        return None

                    data = await response.json()

                    # openInterest 是持仓量（币的数量）
                    oi = float(data.get('openInterest', 0))

                    logger.debug(f"OI for {symbol}: {oi}")
                    return oi

        except Exception as e:
            logger.error(f"Error fetching OI for {symbol}: {e}")
            return None

    async def _get_historical_oi(
        self,
        symbol: str,
        hours: int = 48
    ) -> Optional[float]:
        """
        从Redis获取历史OI

        缓存key格式: oi:{symbol}:48h
        """
        try:
            cache_key = f"oi:{symbol}:{hours}h"
            cached_value = await redis_client.get(cache_key)

            if cached_value:
                return float(cached_value)

            return None

        except Exception as e:
            logger.error(f"Error getting historical OI: {e}")
            return None

    async def _cache_oi(self, symbol: str, oi: float):
        """
        缓存当前OI（48小时过期）
        """
        try:
            cache_key = f"oi:{symbol}:48h"
            # 缓存48小时
            await redis_client.set(cache_key, str(oi), ex=48 * 3600)

        except Exception as e:
            logger.error(f"Error caching OI: {e}")

    def _format_message(
        self,
        symbol: str,
        oi_change_pct: float,
        price_change_pct: float,
        current_oi: float,
        current_price: float
    ) -> str:
        """
        格式化告警消息
        """
        direction = "增加" if oi_change_pct > 0 else "减少"
        emoji = "🟢" if oi_change_pct > 0 else "🔴"

        lines = [
            f"{emoji} OI异常 - 资金提前埋伏",
            f"",
            f"🪙 {symbol}",
            f"💰 现价: ${current_price:,.4f}",
            f"",
            f"📊 48小时变化:",
            f"  • OI变动: {oi_change_pct:+.1f}% {emoji}",
            f"  • 价格变动: {price_change_pct:+.1f}%",
            f"",
            f"🎯 信号解读:",
            f"  • 持仓量{direction}{abs(oi_change_pct):.1f}%",
            f"  • 但价格仅{abs(price_change_pct):.1f}%变化",
            f"  • 说明：资金提前埋伏，价格未反应",
            f"",
            f"⚠️  lana方法:",
            f"  • 这是资金提前布局的信号",
            f"  • 结合其他信号判断方向",
            f"  • 等待价格突破确认",
        ]

        return '\n'.join(lines)


# 扩展Redis客户端方法
async def redis_set(key: str, value: str, ex: int):
    """辅助方法：设置Redis键值"""
    if redis_client.redis:
        await redis_client.redis.set(key, value, ex=ex)


async def redis_get(key: str) -> Optional[str]:
    """辅助方法：获取Redis键值"""
    if redis_client.redis:
        value = await redis_client.redis.get(key)
        return value.decode() if value else None
    return None


# 将方法添加到redis_client
redis_client.set = redis_set
redis_client.get = redis_get
