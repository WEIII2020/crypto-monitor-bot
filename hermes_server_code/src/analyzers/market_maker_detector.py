"""
Market Maker / Manipulation Detector
检测庄家控盘、对敲、吸筹出货等操控行为
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from src.database.redis_client import redis_client
from src.utils.logger import logger


class MarketMakerDetector:
    """
    检测市场操控行为

    核心检测维度：
    1. 长期吸筹识别 (multi-timeframe accumulation)
    2. 价量背离 (price-volume divergence)
    3. 对敲识别 (wash trading)
    4. 拉盘出货 (pump and dump)
    5. 连续模式确认 (pattern confirmation)
    """

    def __init__(self):
        # 时间窗口（分钟）
        self.timeframes = {
            'short': 5,      # 短期：对敲识别
            'medium': 30,    # 中期：吸筹/出货
            'long': 240,     # 长期：趋势确认
            'daily': 1440    # 日线：大周期判断
        }

        # 阈值配置
        self.thresholds = {
            # 对敲识别
            'wash_trading_volume': 10.0,      # 10x平均量
            'wash_trading_price_range': 2.0,   # 价格波动<2%

            # 吸筹识别
            'accumulation_volume': 3.0,        # 3x平均量
            'accumulation_price_drop': -5.0,   # 价格下跌<5%
            'accumulation_consistency': 3,     # 连续3次确认

            # 出货识别
            'distribution_volume': 5.0,        # 5x平均量
            'distribution_price_rise': 15.0,   # 价格上涨>15%
            'distribution_pattern_count': 2,   # 2次确认

            # 背离识别
            'divergence_price_threshold': 10.0,  # 价格创新高>10%
            'divergence_volume_ratio': 0.5,      # 但交易量<50%
        }

        # 模式历史记录 (symbol -> [patterns])
        self.pattern_history = defaultdict(list)
        self.max_history = 20  # 保留最近20个模式

    async def check_manipulation(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[Dict]:
        """
        综合检测市场操控行为

        Returns:
            alert dict if manipulation detected, None otherwise
        """
        try:
            # 获取多时间框架数据
            data = await self._get_multi_timeframe_data(exchange, symbol)
            if not data:
                return None

            # 检测各类模式
            patterns = []

            # 1. 对敲检测 (短期)
            wash_trading = await self._detect_wash_trading(data['short'])
            if wash_trading:
                patterns.append(wash_trading)

            # 2. 吸筹检测 (中长期)
            accumulation = await self._detect_accumulation(
                data['medium'],
                data['long'],
                symbol
            )
            if accumulation:
                patterns.append(accumulation)

            # 3. 出货检测 (中期)
            distribution = await self._detect_distribution(
                data['medium'],
                symbol
            )
            if distribution:
                patterns.append(distribution)

            # 4. 价量背离 (中长期)
            divergence = await self._detect_divergence(
                data['medium'],
                data['long']
            )
            if divergence:
                patterns.append(divergence)

            # 5. 综合评分
            if patterns:
                manipulation_score = self._calculate_manipulation_score(patterns)

                # 只在高风险时发送告警
                if manipulation_score >= 60:
                    # 检查去重
                    alert_key = f"MANIPULATION_{symbol}"
                    already_sent = await redis_client.check_alert_sent(
                        symbol,
                        "MANIPULATION"
                    )

                    if already_sent:
                        return None

                    # 标记已发送 (30分钟冷却)
                    await redis_client.mark_alert_sent(
                        symbol,
                        "MANIPULATION",
                        ttl_seconds=1800
                    )

                    return {
                        'symbol': symbol,
                        'exchange': exchange,
                        'alert_type': 'MARKET_MANIPULATION',
                        'alert_level': self._get_risk_level(manipulation_score),
                        'manipulation_score': manipulation_score,
                        'patterns': patterns,
                        'price': data['short']['latest_price'],
                        'message': self._format_alert_message(
                            symbol,
                            manipulation_score,
                            patterns,
                            data
                        )
                    }

            return None

        except Exception as e:
            logger.error(f"Error checking manipulation for {symbol}: {e}")
            return None

    async def _get_multi_timeframe_data(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[Dict]:
        """获取多时间框架数据"""
        try:
            data = {}

            for tf_name, minutes in self.timeframes.items():
                prices = await redis_client.get_prices(
                    exchange,
                    symbol,
                    minutes=minutes
                )

                if len(prices) < 2:
                    return None

                # 计算统计指标
                latest = prices[0]
                earliest = prices[-1]

                avg_volume = await redis_client.get_avg_volume(
                    exchange,
                    symbol,
                    minutes=minutes * 2  # 用2倍时间作为基准
                )

                data[tf_name] = {
                    'prices': prices,
                    'latest_price': latest['price'],
                    'earliest_price': earliest['price'],
                    'latest_volume': latest['volume'],
                    'avg_volume': avg_volume,
                    'price_change_pct': (
                        (latest['price'] - earliest['price']) / earliest['price'] * 100
                        if earliest['price'] > 0 else 0
                    ),
                    'volume_ratio': (
                        latest['volume'] / avg_volume
                        if avg_volume > 0 else 0
                    ),
                    'high': max(p['price'] for p in prices),
                    'low': min(p['price'] for p in prices),
                }

            return data

        except Exception as e:
            logger.error(f"Error getting multi-timeframe data: {e}")
            return None

    async def _detect_wash_trading(self, data: Dict) -> Optional[Dict]:
        """
        检测对敲 (Wash Trading)

        特征：
        - 极高交易量 (>10x)
        - 价格横盘 (波动<2%)
        - 短期行为
        """
        volume_ratio = data['volume_ratio']
        price_range_pct = (
            (data['high'] - data['low']) / data['earliest_price'] * 100
            if data['earliest_price'] > 0 else 0
        )

        if (volume_ratio >= self.thresholds['wash_trading_volume'] and
            price_range_pct < self.thresholds['wash_trading_price_range']):

            return {
                'type': 'WASH_TRADING',
                'confidence': min(95, int(volume_ratio * 5)),
                'description': '对敲识别：异常放量但价格横盘',
                'metrics': {
                    'volume_ratio': round(volume_ratio, 1),
                    'price_range': round(price_range_pct, 2)
                }
            }

        return None

    async def _detect_accumulation(
        self,
        medium_data: Dict,
        long_data: Dict,
        symbol: str
    ) -> Optional[Dict]:
        """
        检测吸筹 (Accumulation)

        特征：
        - 放量 (>3x)
        - 价格不涨/微跌
        - 连续出现多次
        """
        volume_ratio = medium_data['volume_ratio']
        price_change = medium_data['price_change_pct']

        # 单次吸筹信号
        if (volume_ratio >= self.thresholds['accumulation_volume'] and
            price_change <= self.thresholds['accumulation_price_drop']):

            # 记录到历史
            pattern = {
                'type': 'accumulation',
                'timestamp': datetime.now(),
                'volume_ratio': volume_ratio,
                'price_change': price_change
            }
            self._add_to_history(symbol, pattern)

            # 检查连续性
            recent_accumulations = self._count_recent_patterns(
                symbol,
                'accumulation',
                minutes=240  # 4小时内
            )

            if recent_accumulations >= self.thresholds['accumulation_consistency']:
                return {
                    'type': 'ACCUMULATION_CONFIRMED',
                    'confidence': min(90, 60 + recent_accumulations * 10),
                    'description': f'确认吸筹：{recent_accumulations}次连续信号',
                    'metrics': {
                        'current_volume_ratio': round(volume_ratio, 1),
                        'current_price_change': round(price_change, 2),
                        'pattern_count': recent_accumulations,
                        'long_term_trend': round(long_data['price_change_pct'], 2)
                    }
                }

        return None

    async def _detect_distribution(
        self,
        medium_data: Dict,
        symbol: str
    ) -> Optional[Dict]:
        """
        检测出货 (Distribution)

        特征：
        - 大幅放量 (>5x)
        - 价格大幅拉升 (>15%)
        - 可能在吸筹后发生
        """
        volume_ratio = medium_data['volume_ratio']
        price_change = medium_data['price_change_pct']

        if (volume_ratio >= self.thresholds['distribution_volume'] and
            price_change >= self.thresholds['distribution_price_rise']):

            # 检查是否之前有吸筹
            recent_accumulations = self._count_recent_patterns(
                symbol,
                'accumulation',
                minutes=1440  # 24小时内
            )

            confidence = 70
            description = '疑似出货：放量拉升'

            if recent_accumulations >= 2:
                confidence = 95
                description = f'确认出货：{recent_accumulations}次吸筹后拉升'

            return {
                'type': 'DISTRIBUTION',
                'confidence': confidence,
                'description': description,
                'metrics': {
                    'volume_ratio': round(volume_ratio, 1),
                    'price_change': round(price_change, 2),
                    'prior_accumulation_count': recent_accumulations
                }
            }

        return None

    async def _detect_divergence(
        self,
        medium_data: Dict,
        long_data: Dict
    ) -> Optional[Dict]:
        """
        检测价量背离 (Price-Volume Divergence)

        特征：
        - 价格创新高但交易量萎缩
        - 或价格下跌但交易量放大
        """
        medium_price_change = medium_data['price_change_pct']
        medium_volume_ratio = medium_data['volume_ratio']
        long_volume_ratio = long_data['volume_ratio']

        # 顶背离：价格大涨但量萎缩
        if (medium_price_change >= self.thresholds['divergence_price_threshold'] and
            medium_volume_ratio < self.thresholds['divergence_volume_ratio']):

            return {
                'type': 'BEARISH_DIVERGENCE',
                'confidence': 75,
                'description': '顶背离：价格新高但量能不足',
                'metrics': {
                    'price_change': round(medium_price_change, 2),
                    'volume_ratio': round(medium_volume_ratio, 2),
                    'long_volume_ratio': round(long_volume_ratio, 2)
                }
            }

        # 底背离：价格大跌但量放大（可能是洗盘）
        if (medium_price_change <= -self.thresholds['divergence_price_threshold'] and
            medium_volume_ratio >= 3.0):

            return {
                'type': 'BULLISH_DIVERGENCE',
                'confidence': 70,
                'description': '底背离：价格下跌但放量（可能洗盘）',
                'metrics': {
                    'price_change': round(medium_price_change, 2),
                    'volume_ratio': round(medium_volume_ratio, 2)
                }
            }

        return None

    def _calculate_manipulation_score(self, patterns: List[Dict]) -> int:
        """
        计算综合操控评分 (0-100)

        评分规则：
        - 每个模式贡献基础分 (根据confidence)
        - 多个模式叠加有加成
        - ACCUMULATION_CONFIRMED + DISTRIBUTION = 极高风险
        """
        if not patterns:
            return 0

        base_score = sum(p['confidence'] for p in patterns) / len(patterns)

        # 检查关键组合
        pattern_types = set(p['type'] for p in patterns)

        # 吸筹后出货 = 极高风险
        if 'ACCUMULATION_CONFIRMED' in pattern_types and 'DISTRIBUTION' in pattern_types:
            base_score = min(100, base_score * 1.5)

        # 对敲 + 吸筹 = 高风险
        elif 'WASH_TRADING' in pattern_types and 'ACCUMULATION_CONFIRMED' in pattern_types:
            base_score = min(100, base_score * 1.3)

        # 顶背离 + 出货 = 高风险
        elif 'BEARISH_DIVERGENCE' in pattern_types and 'DISTRIBUTION' in pattern_types:
            base_score = min(100, base_score * 1.4)

        return int(base_score)

    def _get_risk_level(self, score: int) -> str:
        """根据评分返回风险等级"""
        if score >= 80:
            return 'EXTREME'
        elif score >= 60:
            return 'CRITICAL'
        elif score >= 40:
            return 'WARNING'
        else:
            return 'INFO'

    def _add_to_history(self, symbol: str, pattern: Dict):
        """添加模式到历史记录"""
        self.pattern_history[symbol].append(pattern)

        # 限制历史长度
        if len(self.pattern_history[symbol]) > self.max_history:
            self.pattern_history[symbol] = self.pattern_history[symbol][-self.max_history:]

    def _count_recent_patterns(
        self,
        symbol: str,
        pattern_type: str,
        minutes: int
    ) -> int:
        """统计最近时间窗口内的模式数量"""
        if symbol not in self.pattern_history:
            return 0

        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        count = sum(
            1 for p in self.pattern_history[symbol]
            if p['type'] == pattern_type and p['timestamp'] >= cutoff_time
        )

        return count

    def _format_alert_message(
        self,
        symbol: str,
        score: int,
        patterns: List[Dict],
        data: Dict
    ) -> str:
        """格式化告警消息"""

        # 风险等级emoji
        risk_emoji = {
            'EXTREME': '🚨',
            'CRITICAL': '🔴',
            'WARNING': '🟡',
            'INFO': '🟢'
        }

        level = self._get_risk_level(score)
        emoji = risk_emoji.get(level, '⚠️')

        # 构建消息
        lines = [
            f"{emoji} 庄家操控检测 ({score}分/{level})",
            f"📈 {symbol}",
            f"💰 当前价格: ${data['short']['latest_price']:,.4f}",
            f"📊 30分钟涨跌: {'+' if data['medium']['price_change_pct'] >= 0 else ''}{data['medium']['price_change_pct']:.2f}%",
            "",
            "🔍 检测到的模式:"
        ]

        for pattern in patterns:
            confidence_bar = '█' * (pattern['confidence'] // 10)
            lines.append(f"  {pattern['type']}: {confidence_bar} {pattern['confidence']}%")
            lines.append(f"  └─ {pattern['description']}")

            if 'metrics' in pattern:
                for key, value in pattern['metrics'].items():
                    lines.append(f"     • {key}: {value}")

        # 操作建议
        lines.append("")
        lines.append("⚡ 风险提示:")

        if score >= 80:
            lines.append("  🔴 极高风险：疑似庄家绝对控盘")
            lines.append("  🔴 避免追高：可能拉盘出货")
            lines.append("  🔴 避免抄底：可能继续下跌")
        elif score >= 60:
            lines.append("  🟡 高风险：检测到操控行为")
            lines.append("  🟡 谨慎交易：等待信号确认")

        return '\n'.join(lines)
