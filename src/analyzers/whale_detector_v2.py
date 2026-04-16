"""
Whale/Market Maker Behavior Detector V2
增强版：多时间框架分析 + 趋势确认

保持向后兼容，同时增加：
1. 多时间框架分析 (5min, 30min, 4h)
2. 模式确认机制 (连续信号)
3. 更精准的告警去重
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from src.database.redis_client import redis_client
from src.utils.logger import logger


class WhaleDetectorV2:
    """升级版巨鲸检测器"""

    def __init__(self):
        # 原有阈值（保持向后兼容）
        self.volume_spike_threshold = 5.0
        self.volume_low_threshold = 2.0
        self.sideways_threshold = 3.0
        self.significant_rise = 10.0
        self.moderate_rise = 8.0
        self.significant_drop = 10.0

        # 新增：多时间框架配置
        self.timeframes = {
            'short': 5,      # 5分钟：快速信号
            'medium': 30,    # 30分钟：趋势确认
            'long': 240,     # 4小时：大趋势
        }

        # 新增：模式历史记录
        self.pattern_history = defaultdict(list)
        self.max_history = 50  # 保留最近50个模式

        # 新增：确认阈值
        self.confirmation_thresholds = {
            'accumulation': 3,    # 吸筹需要3次确认
            'distribution': 2,    # 出货需要2次确认
            'fake_breakout': 2,   # 假突破需要2次确认
        }

    async def check_whale_activity(
        self,
        exchange: str,
        symbol: str,
        use_multi_timeframe: bool = True
    ) -> Optional[Dict]:
        """
        检测巨鲸活动

        Args:
            exchange: 交易所
            symbol: 交易对
            use_multi_timeframe: 是否使用多时间框架（默认True）

        Returns:
            alert dict or None
        """
        try:
            if use_multi_timeframe:
                return await self._check_multi_timeframe(exchange, symbol)
            else:
                # 向后兼容：使用原有的单时间框架逻辑
                return await self._check_single_timeframe(exchange, symbol)

        except Exception as e:
            logger.error(f"Error checking whale activity for {symbol}: {e}")
            return None

    async def _check_single_timeframe(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[Dict]:
        """
        原有的单时间框架检测逻辑（5分钟）
        保持向后兼容
        """
        # 获取5分钟数据
        recent_prices = await redis_client.get_prices(exchange, symbol, minutes=5)
        if len(recent_prices) < 2:
            return None

        avg_volume = await redis_client.get_avg_volume(exchange, symbol, minutes=60)
        if avg_volume == 0:
            return None

        # 计算指标
        latest_price = recent_prices[0]['price']
        earliest_price = recent_prices[-1]['price']
        current_volume = recent_prices[0]['volume']

        if earliest_price == 0:
            return None

        price_change_pct = ((latest_price - earliest_price) / earliest_price) * 100
        volume_multiplier = current_volume / avg_volume if avg_volume > 0 else 0

        # 检测模式
        pattern = self._detect_pattern(price_change_pct, volume_multiplier)

        if pattern:
            # 去重检查
            alert_key = f"{symbol}_WHALE_{pattern['type']}"
            already_sent = await redis_client.check_alert_sent(
                symbol,
                f"WHALE_{pattern['type']}"
            )

            if already_sent:
                logger.debug(f"Whale alert already sent for {symbol}, skipping")
                return None

            # 标记已发送
            await redis_client.mark_alert_sent(
                symbol,
                f"WHALE_{pattern['type']}",
                ttl_seconds=600
            )

            return {
                'symbol': symbol,
                'exchange': exchange,
                'alert_type': 'WHALE_ACTIVITY',
                'alert_level': pattern['level'],
                'pattern': pattern['type'],
                'price': latest_price,
                'change_percent': round(price_change_pct, 2),
                'volume_multiplier': round(volume_multiplier, 1),
                'message': self._format_message(
                    symbol,
                    pattern,
                    price_change_pct,
                    volume_multiplier,
                    latest_price
                )
            }

        return None

    async def _check_multi_timeframe(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[Dict]:
        """
        多时间框架检测逻辑（新增）

        分析短期、中期、长期趋势，只在信号确认时告警
        """
        # 获取多时间框架数据
        tf_data = {}
        for tf_name, minutes in self.timeframes.items():
            prices = await redis_client.get_prices(exchange, symbol, minutes=minutes)
            if len(prices) < 2:
                return None

            avg_volume = await redis_client.get_avg_volume(
                exchange,
                symbol,
                minutes=minutes * 2
            )

            latest = prices[0]
            earliest = prices[-1]

            tf_data[tf_name] = {
                'price_change_pct': (
                    (latest['price'] - earliest['price']) / earliest['price'] * 100
                    if earliest['price'] > 0 else 0
                ),
                'volume_ratio': (
                    latest['volume'] / avg_volume
                    if avg_volume > 0 else 0
                ),
                'latest_price': latest['price'],
                'latest_volume': latest['volume']
            }

        # 短期信号检测
        short_pattern = self._detect_pattern(
            tf_data['short']['price_change_pct'],
            tf_data['short']['volume_ratio']
        )

        if not short_pattern:
            return None

        # 记录到历史
        self._add_pattern_to_history(
            symbol,
            short_pattern['type'],
            tf_data['short']
        )

        # 检查中长期趋势确认
        confirmation = self._check_confirmation(
            symbol,
            short_pattern['type'],
            tf_data
        )

        if confirmation:
            # 只在确认后才发送告警
            alert_key = f"WHALE_CONFIRMED_{short_pattern['type']}"
            already_sent = await redis_client.check_alert_sent(symbol, alert_key)

            if already_sent:
                return None

            # 更长的冷却时间（30分钟）
            await redis_client.mark_alert_sent(symbol, alert_key, ttl_seconds=1800)

            return {
                'symbol': symbol,
                'exchange': exchange,
                'alert_type': 'WHALE_ACTIVITY_CONFIRMED',
                'alert_level': confirmation['level'],
                'pattern': short_pattern['type'],
                'confirmation_count': confirmation['count'],
                'timeframe': 'MULTI',
                'price': tf_data['short']['latest_price'],
                'change_percent_5m': round(tf_data['short']['price_change_pct'], 2),
                'change_percent_30m': round(tf_data['medium']['price_change_pct'], 2),
                'change_percent_4h': round(tf_data['long']['price_change_pct'], 2),
                'volume_ratio': round(tf_data['short']['volume_ratio'], 1),
                'message': self._format_multi_timeframe_message(
                    symbol,
                    short_pattern,
                    confirmation,
                    tf_data
                )
            }

        return None

    def _detect_pattern(
        self,
        price_change_pct: float,
        volume_multiplier: float
    ) -> Optional[Dict]:
        """
        检测模式（原有逻辑）
        """
        abs_price_change = abs(price_change_pct)

        # 吸筹
        if abs_price_change < self.sideways_threshold and volume_multiplier >= self.volume_spike_threshold:
            return {
                'type': 'ACCUMULATION',
                'level': 'WARNING',
                'description': '放量不涨，疑似吸筹'
            }

        # 出货
        if price_change_pct >= self.significant_rise and volume_multiplier >= self.volume_spike_threshold:
            return {
                'type': 'DISTRIBUTION',
                'level': 'CRITICAL',
                'description': '放量拉升，疑似出货'
            }

        # 假突破
        if price_change_pct >= self.moderate_rise and volume_multiplier < self.volume_low_threshold:
            return {
                'type': 'FAKE_BREAKOUT',
                'level': 'WARNING',
                'description': '缩量上涨，警惕假突破'
            }

        # 恐慌
        if price_change_pct <= -self.significant_drop and volume_multiplier >= self.volume_spike_threshold:
            return {
                'type': 'PANIC_SELL',
                'level': 'CRITICAL',
                'description': '放量下跌，恐慌出逃'
            }

        # 异常放量
        if volume_multiplier >= 10.0 and abs_price_change < self.significant_rise:
            return {
                'type': 'VOLUME_SPIKE',
                'level': 'WARNING',
                'description': '异常放量，可能对敲'
            }

        return None

    def _add_pattern_to_history(
        self,
        symbol: str,
        pattern_type: str,
        data: Dict
    ):
        """添加模式到历史记录"""
        self.pattern_history[symbol].append({
            'type': pattern_type,
            'timestamp': datetime.now(),
            'price_change': data['price_change_pct'],
            'volume_ratio': data['volume_ratio']
        })

        # 限制历史长度
        if len(self.pattern_history[symbol]) > self.max_history:
            self.pattern_history[symbol] = self.pattern_history[symbol][-self.max_history:]

    def _check_confirmation(
        self,
        symbol: str,
        pattern_type: str,
        tf_data: Dict
    ) -> Optional[Dict]:
        """
        检查模式确认

        规则：
        - ACCUMULATION: 需要3次以上，且中长期趋势向下或横盘
        - DISTRIBUTION: 需要2次以上，且中长期趋势向上
        - FAKE_BREAKOUT: 需要2次以上
        """
        if symbol not in self.pattern_history:
            return None

        # 统计最近30分钟内的相同模式
        cutoff_time = datetime.now() - timedelta(minutes=30)
        recent_patterns = [
            p for p in self.pattern_history[symbol]
            if p['type'] == pattern_type and p['timestamp'] >= cutoff_time
        ]

        count = len(recent_patterns)

        # 根据模式类型判断是否确认
        if pattern_type == 'ACCUMULATION':
            threshold = self.confirmation_thresholds['accumulation']
            # 吸筹：中长期应该是横盘或下跌
            medium_trend = tf_data['medium']['price_change_pct']
            if count >= threshold and medium_trend <= 5.0:
                return {
                    'confirmed': True,
                    'count': count,
                    'level': 'CRITICAL' if count >= 5 else 'WARNING',
                    'reason': f'连续{count}次吸筹信号，中期趋势横盘'
                }

        elif pattern_type == 'DISTRIBUTION':
            threshold = self.confirmation_thresholds['distribution']
            # 出货：中期应该是上涨
            medium_trend = tf_data['medium']['price_change_pct']
            if count >= threshold and medium_trend >= 10.0:
                return {
                    'confirmed': True,
                    'count': count,
                    'level': 'CRITICAL',
                    'reason': f'连续{count}次出货信号，中期上涨{medium_trend:.1f}%'
                }

        elif pattern_type == 'FAKE_BREAKOUT':
            threshold = self.confirmation_thresholds['fake_breakout']
            if count >= threshold:
                return {
                    'confirmed': True,
                    'count': count,
                    'level': 'WARNING',
                    'reason': f'连续{count}次假突破信号'
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
        """原有的消息格式（保持向后兼容）"""
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
        message += f"💰 价格: ${price:,.4f}\n"
        message += f"📊 涨跌: {'+' if price_change >= 0 else ''}{price_change:.2f}%\n"
        message += f"🔊 交易量: {volume_mult:.1f}x 平均值"

        return message

    def _format_multi_timeframe_message(
        self,
        symbol: str,
        pattern: Dict,
        confirmation: Dict,
        tf_data: Dict
    ) -> str:
        """多时间框架消息格式（新增）"""
        emoji_map = {
            'ACCUMULATION': '🟢',
            'DISTRIBUTION': '🔴',
            'FAKE_BREAKOUT': '⚠️',
            'PANIC_SELL': '💀',
            'VOLUME_SPIKE': '📊'
        }

        emoji = emoji_map.get(pattern['type'], '🐋')
        level_emoji = '🚨' if confirmation['level'] == 'CRITICAL' else '⚠️'

        lines = [
            f"{level_emoji} {emoji} 确认信号: {pattern['description']}",
            f"📈 {symbol}",
            f"💰 当前价格: ${tf_data['short']['latest_price']:,.4f}",
            "",
            "📊 多时间框架分析:",
            f"  • 5分钟:  {'+' if tf_data['short']['price_change_pct'] >= 0 else ''}{tf_data['short']['price_change_pct']:.2f}%  (量: {tf_data['short']['volume_ratio']:.1f}x)",
            f"  • 30分钟: {'+' if tf_data['medium']['price_change_pct'] >= 0 else ''}{tf_data['medium']['price_change_pct']:.2f}%  (量: {tf_data['medium']['volume_ratio']:.1f}x)",
            f"  • 4小时:  {'+' if tf_data['long']['price_change_pct'] >= 0 else ''}{tf_data['long']['price_change_pct']:.2f}%  (量: {tf_data['long']['volume_ratio']:.1f}x)",
            "",
            f"✅ 确认信息:",
            f"  • {confirmation['reason']}",
            f"  • 信号强度: {confirmation['level']}",
        ]

        # 根据模式类型添加操作建议
        if pattern['type'] == 'ACCUMULATION':
            lines.append("")
            lines.append("💡 操作建议:")
            lines.append("  🟢 庄家可能在吸筹")
            lines.append("  🟢 关注后续拉盘信号")
            lines.append("  ⚠️  避免追涨杀跌")

        elif pattern['type'] == 'DISTRIBUTION':
            lines.append("")
            lines.append("💡 操作建议:")
            lines.append("  🔴 庄家可能在出货")
            lines.append("  🔴 避免追高")
            lines.append("  🔴 考虑止盈")

        elif pattern['type'] == 'FAKE_BREAKOUT':
            lines.append("")
            lines.append("💡 操作建议:")
            lines.append("  ⚠️  警惕假突破")
            lines.append("  ⚠️  等待放量确认")
            lines.append("  ⚠️  设置止损")

        return '\n'.join(lines)
