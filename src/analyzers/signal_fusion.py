"""
Signal Fusion - 信号融合器
整合多个信号源，计算综合评分，实现 lana 的多维度判断逻辑
"""

from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime

from src.utils.logger import logger


@dataclass
class Signal:
    """单个信号"""
    type: str  # 信号类型
    symbol: str
    score: int  # 评分 (0-100)
    data: Dict  # 原始数据
    timestamp: datetime


class SignalFusion:
    """
    信号融合器

    核心逻辑（lana方法的精髓）：
    1. 价格波动（技术面） - 30分
    2. 巨鲸行为（资金面） - 20分
    3. OI变动（期货面） - 40分  ← lana的核心信号
    4. 广场热度（情绪面） - 10分  ← lana的核心信号

    综合评分 ≥ 60分 = WATCH（观察）
    综合评分 ≥ 80分 = BUY（买入信号）
    """

    def __init__(self):
        # 评分权重（lana方法）
        self.weights = {
            'PRICE_SPIKE': 30,      # 价格突变
            'WHALE_ACTIVITY': 20,   # 巨鲸活动
            'OI_SPIKE': 40,         # OI异常（最重要）
            'SQUARE_TRENDING': 10,  # 广场热度
            'PUMP_DETECTED': 30,    # 暴涨检测（朋友的方法）
        }

        # 行动阈值（优化后 - 更谨慎）
        self.watch_threshold = 65   # 观察（提高门槛）
        self.buy_threshold = 85     # 买入（更谨慎）

    async def fuse_signals(
        self,
        symbol: str,
        signals: List[Dict]
    ) -> Optional[Dict]:
        """
        融合多个信号，计算综合评分

        Args:
            symbol: 币种
            signals: 信号列表

        Returns:
            融合后的信号，包含综合评分和建议
        """
        try:
            if not signals:
                return None

            # 1. 计算基础分数
            total_score = 0
            signal_details = []

            for signal in signals:
                signal_type = signal.get('alert_type')
                signal_score = signal.get('score', 0)

                # 应用权重
                weighted_score = self._apply_weight(signal_type, signal_score)

                total_score += weighted_score
                signal_details.append({
                    'type': signal_type,
                    'score': weighted_score,
                    'data': signal
                })

            # 2. 检查信号组合加成
            bonus = self._calculate_bonus(signals)
            total_score += bonus

            # 3. 限制总分在0-100之间
            total_score = min(100, max(0, total_score))

            # 4. 判断行动等级
            if total_score < self.watch_threshold:
                return None  # 分数不够，不发告警

            action = self._determine_action(total_score)
            alert_level = self._determine_alert_level(total_score)

            # 5. 获取价格信息（从任意信号中）
            current_price = self._extract_price(signals)

            logger.info(
                f"🎯 信号融合: {symbol} | "
                f"综合评分{total_score}分 | "
                f"行动:{action}"
            )

            # 6. 构建融合信号
            return {
                'symbol': symbol,
                'exchange': 'binance',
                'alert_type': 'SIGNAL_FUSION',
                'alert_level': alert_level,
                'total_score': total_score,
                'action': action,
                'signal_count': len(signals),
                'signal_details': signal_details,
                'bonus': bonus,
                'current_price': current_price,
                'message': self._format_message(
                    symbol,
                    total_score,
                    action,
                    signal_details,
                    bonus,
                    current_price
                )
            }

        except Exception as e:
            logger.error(f"Error fusing signals for {symbol}: {e}")
            return None

    def _apply_weight(self, signal_type: str, signal_score: int) -> int:
        """
        应用信号权重

        lana方法：不同信号的重要性不同
        OI变动 > 价格波动 > 巨鲸 > 广场热度
        """
        weight = self.weights.get(signal_type, 10)

        # 信号本身的score是0-100，但权重限制了最大分数
        # 例如：OI_SPIKE权重40，即使信号score=100，最多贡献40分
        return min(weight, int(signal_score * weight / 100))

    def _calculate_bonus(self, signals: List[Dict]) -> int:
        """
        计算信号组合加成

        lana方法的关键：某些信号组合特别有效
        """
        bonus = 0
        signal_types = set(s.get('alert_type') for s in signals)

        # 黄金组合1：OI异常 + 价格波动 = +15分
        if 'OI_SPIKE' in signal_types and 'PRICE_SPIKE' in signal_types:
            bonus += 15
            logger.debug("组合加成: OI异常+价格波动 = +15分")

        # 黄金组合2：OI异常 + 广场热度 = +10分
        # lana逻辑：资金埋伏 + 散户关注 = 即将启动
        if 'OI_SPIKE' in signal_types and 'SQUARE_TRENDING' in signal_types:
            bonus += 10
            logger.debug("组合加成: OI异常+广场热度 = +10分")

        # 黄金组合3：巨鲸买入 + 广场热度 = +8分
        # 散户和大户同时进场
        if 'WHALE_ACTIVITY' in signal_types and 'SQUARE_TRENDING' in signal_types:
            bonus += 8
            logger.debug("组合加成: 巨鲸+广场热度 = +8分")

        # 组合4：朋友的妖币方法 + OI异常 = +20分
        # 暴涨确认 + 资金提前埋伏 = 高确定性
        if 'PUMP_DETECTED' in signal_types and 'OI_SPIKE' in signal_types:
            bonus += 20
            logger.debug("组合加成: 暴涨+OI异常 = +20分")

        return bonus

    def _determine_action(self, score: int) -> str:
        """
        根据评分决定行动

        lana规则：
        - 60-79分：WATCH（观察，不入场）
        - 80-100分：BUY（买入信号）
        """
        if score >= self.buy_threshold:
            return 'BUY'
        elif score >= self.watch_threshold:
            return 'WATCH'
        else:
            return 'IGNORE'

    def _determine_alert_level(self, score: int) -> str:
        """根据评分决定告警等级"""
        if score >= 90:
            return 'CRITICAL'
        elif score >= 80:
            return 'WARNING'
        else:
            return 'INFO'

    def _extract_price(self, signals: List[Dict]) -> Optional[float]:
        """从信号中提取当前价格"""
        for signal in signals:
            if 'current_price' in signal:
                return signal['current_price']
            if 'price' in signal:
                return signal['price']
        return None

    def _format_message(
        self,
        symbol: str,
        total_score: int,
        action: str,
        signal_details: List[Dict],
        bonus: int,
        current_price: Optional[float]
    ) -> str:
        """
        格式化融合信号消息
        """
        # 行动emoji
        action_emoji = {
            'BUY': '🟢',
            'WATCH': '🟡',
            'IGNORE': '⚪'
        }

        emoji = action_emoji.get(action, '⚪')

        lines = [
            f"{emoji} 综合信号 - {action}",
            f"",
            f"🪙 {symbol}",
        ]

        if current_price:
            lines.append(f"💰 现价: ${current_price:,.4f}")

        lines.extend([
            f"",
            f"📊 综合评分: {total_score}/100",
            f"",
            f"🔍 触发信号 ({len(signal_details)}个):",
        ])

        # 列出所有信号
        for detail in signal_details:
            signal_type = detail['type']
            signal_score = detail['score']
            lines.append(f"  • {signal_type}: {signal_score}分")

        if bonus > 0:
            lines.extend([
                f"",
                f"⚡ 组合加成: +{bonus}分",
            ])

        lines.extend([
            f"",
            f"🎯 建议行动: {action}",
        ])

        # 根据行动给出具体建议
        if action == 'BUY':
            lines.extend([
                f"",
                f"✅ 买入信号确认:",
                f"  • 多个信号同时触发",
                f"  • 综合评分达到{total_score}分",
                f"  • 建议：轻仓试探",
                f"  • 止损：严格执行（lana规则：亏200u出）",
            ])
        elif action == 'WATCH':
            lines.extend([
                f"",
                f"👀 观察模式:",
                f"  • 信号尚未完全确认",
                f"  • 综合评分{total_score}分（需≥80）",
                f"  • 建议：密切关注，等待更多信号",
            ])

        lines.extend([
            f"",
            f"⚠️  lana方法:",
            f"  • 规则执行 > 主观判断",
            f"  • 亏200u立即止损",
            f"  • 只做一个方向，不做反向",
        ])

        return '\n'.join(lines)


# 全局单例
signal_fusion = SignalFusion()
