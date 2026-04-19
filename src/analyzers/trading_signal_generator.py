"""
Trading Signal Generator - 交易信号生成器

整合多个策略，生成统一格式的交易信号：
- V4A: 支撑崩塌做空
- V7: 价格OI背离做空
- V8: 插针+OI骤降做空
- LONG: 反弹做多

输出格式：适合 Telegram 推送和 Hermes Agent 集成
"""

from typing import Dict, Optional, List
from datetime import datetime
from dataclasses import dataclass
import asyncio

from src.analyzers.manipulation_detector_v2 import ManipulationDetectorV2, ManipulationScore
from src.utils.logger import logger


@dataclass
class TradingSignal:
    """交易信号"""
    signal_id: str
    symbol: str
    strategy: str  # V4A, V7, V8, LONG
    direction: str  # LONG, SHORT
    timestamp: datetime

    # 入场信息
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float]

    # 风险管理
    position_size: str
    max_holding_hours: Optional[float]
    risk_level: str

    # 信号质量
    confidence: int  # 0-100
    manipulation_score: Optional[int]

    # 详细数据
    market_data: Dict
    note: str


class TradingSignalGenerator:
    """
    交易信号生成器

    功能：
    1. 整合 V4A/V7/V8/LONG 策略
    2. 统一信号格式
    3. 信号优先级排序
    4. 防重复告警
    """

    def __init__(self):
        self.manipulation_detector = ManipulationDetectorV2()

        # 信号冷却期（秒）
        self.signal_cooldown = {
            'V4A_SHORT': 14400,  # 4 小时
            'V7_SHORT': 14400,   # 4 小时
            'V8_SHORT': 7200,    # 2 小时
            'LONG': 7200         # 2 小时
        }

        # 信号历史（防重复）
        self.signal_history = {}  # {symbol: {strategy: last_timestamp}}

        # 冷却期锁（防止并发竞态条件）
        self._cooldown_locks = {}  # {symbol:strategy: Lock}

    async def generate_signals(
        self,
        symbol: str,
        realtime_data: Dict,
        historical_data: Dict,
        market_data: Dict
    ) -> List[TradingSignal]:
        """
        生成交易信号

        Args:
            symbol: 币种
            realtime_data: 实时数据（来自 Phase 1）
            historical_data: 历史数据（4h, 6h, 24h）
            market_data: 市场数据（OI, 资金费率等）

        Returns:
            交易信号列表
        """
        signals = []

        try:
            # 1. 计算操纵评分
            manipulation_score = await self.manipulation_detector.calculate_manipulation_score(
                symbol, market_data
            )

            if not manipulation_score:
                # 注意：不记录日志，因为大部分币种都是正常币（非妖币）
                return []

            # 2. 检测各类信号
            # V4A: 支撑崩塌做空
            v4a_signal = await self.manipulation_detector.detect_v4a_signal(
                symbol, realtime_data, manipulation_score
            )
            if v4a_signal and await self._check_cooldown(symbol, 'V4A_SHORT'):
                signals.append(self._format_signal(v4a_signal, manipulation_score))

            # V7: 价格OI背离做空
            v7_signal = await self.manipulation_detector.detect_v7_signal(
                symbol, historical_data
            )
            if v7_signal and await self._check_cooldown(symbol, 'V7_SHORT'):
                signals.append(self._format_signal(v7_signal, manipulation_score))

            # V8: 插针+OI骤降做空
            v8_signal = await self.manipulation_detector.detect_v8_signal(
                symbol, realtime_data, manipulation_score
            )
            if v8_signal and await self._check_cooldown(symbol, 'V8_SHORT'):
                signals.append(self._format_signal(v8_signal, manipulation_score))

            # LONG: 反弹做多
            long_signal = await self.manipulation_detector.detect_long_signal(
                symbol, realtime_data, manipulation_score
            )
            if long_signal and await self._check_cooldown(symbol, 'LONG'):
                signals.append(self._format_signal(long_signal, manipulation_score))

            # 3. 按优先级排序
            signals.sort(key=lambda x: x.confidence, reverse=True)

            return signals

        except Exception as e:
            logger.error(f"Error generating signals for {symbol}: {e}")
            return []

    def _format_signal(self, raw_signal: Dict, manipulation_score: ManipulationScore) -> TradingSignal:
        """格式化信号"""
        signal_type = raw_signal['type']
        strategy = raw_signal['strategy']
        direction = raw_signal['direction']

        # 计算置信度
        confidence = self._calculate_confidence(raw_signal, manipulation_score)

        # 生成唯一 ID
        signal_id = f"{raw_signal['symbol']}_{signal_type}_{int(datetime.now().timestamp())}"

        # 提取止盈目标
        take_profit_1 = raw_signal.get('take_profit_1')
        take_profit_2 = raw_signal.get('take_profit_2')

        # 如果没有明确的止盈，根据方向计算
        if not take_profit_1:
            entry = raw_signal['entry_price']
            if direction == 'SHORT':
                take_profit_1 = entry * 0.95  # -5%
                take_profit_2 = entry * 0.90  # -10%
            else:  # LONG
                take_profit_1 = entry * 1.05  # +5%
                take_profit_2 = entry * 1.08  # +8%

        return TradingSignal(
            signal_id=signal_id,
            symbol=raw_signal['symbol'],
            strategy=signal_type,
            direction=direction,
            timestamp=raw_signal['timestamp'],

            entry_price=raw_signal['entry_price'],
            stop_loss=raw_signal['stop_loss'],
            take_profit_1=take_profit_1,
            take_profit_2=take_profit_2,

            position_size=raw_signal.get('position_size', '5-10%'),
            max_holding_hours=raw_signal.get('max_holding_hours'),
            risk_level=raw_signal.get('risk', 'HIGH'),

            confidence=confidence,
            manipulation_score=manipulation_score.score,

            market_data=raw_signal,
            note=raw_signal.get('note', '')
        )

    def _calculate_confidence(self, signal: Dict, manipulation_score: ManipulationScore) -> int:
        """
        计算信号置信度（0-100）

        考虑因素：
        - 策略类型
        - 操纵评分
        - 信号强度
        """
        confidence = 50  # 基础分

        signal_type = signal['type']

        # 策略权重
        strategy_weights = {
            'V8_SHORT': 30,  # V8 最强（快 2-4 小时）
            'V4A_SHORT': 25,  # V4A 次之（早进）
            'V7_SHORT': 20,  # V7 第三（背离）
            'LONG': 15       # 做多最保守
        }
        confidence += strategy_weights.get(signal_type, 0)

        # 操纵评分加成
        if manipulation_score.risk_level == 'EXTREME':
            confidence += 15
        elif manipulation_score.risk_level == 'HIGH':
            confidence += 10

        # 信号强度加成
        if signal_type == 'V4A_SHORT':
            # 支撑跌破幅度越大越好
            support_break = signal.get('support_break') or 0
            if support_break > 5:
                confidence += 10
            elif support_break > 3:
                confidence += 5

        elif signal_type == 'V7_SHORT':
            # 背离强度越大越好
            divergence = signal.get('divergence_strength') or 0
            if divergence > 20:
                confidence += 10
            elif divergence > 15:
                confidence += 5

        elif signal_type == 'V8_SHORT':
            # 插针+OI骤降幅度越大越好
            wick = signal.get('upper_wick_pct') or 0
            oi_drop = abs(signal.get('oi_drop_30m') or 0)
            if wick > 8 and oi_drop > 20:
                confidence += 15
            elif wick > 5 and oi_drop > 15:
                confidence += 10

        elif signal_type == 'LONG':
            # 买方主导程度
            buy_ratio = signal.get('buy_ratio') or 50
            if buy_ratio > 80:
                confidence += 10
            elif buy_ratio > 70:
                confidence += 5

        # 限制在 0-100
        return min(100, max(0, confidence))

    async def _check_cooldown(self, symbol: str, strategy: str) -> bool:
        """
        检查冷却期（线程安全）

        Args:
            symbol: 币种
            strategy: 策略类型

        Returns:
            True=可以发信号, False=在冷却期
        """
        # 为每个 symbol:strategy 组合创建独立的锁
        lock_key = f"{symbol}:{strategy}"
        if lock_key not in self._cooldown_locks:
            self._cooldown_locks[lock_key] = asyncio.Lock()

        # 使用锁保护临界区，防止并发竞态
        async with self._cooldown_locks[lock_key]:
            if symbol not in self.signal_history:
                self.signal_history[symbol] = {}

            last_time = self.signal_history[symbol].get(strategy)

            if not last_time:
                # 首次发信号
                self.signal_history[symbol][strategy] = datetime.now()
                return True

            # 检查是否过了冷却期
            elapsed = (datetime.now() - last_time).total_seconds()
            cooldown = self.signal_cooldown.get(strategy, 3600)

            if elapsed >= cooldown:
                self.signal_history[symbol][strategy] = datetime.now()
                return True

            return False

    def format_telegram_message(self, signal: TradingSignal) -> str:
        """
        格式化 Telegram 消息

        输出示例：
        ╔════════════════════════════
        ║ 🔴 做空信号 - ETHUSDT
        ║ 策略: V4A 支撑崩塌
        ╠════════════════════════════
        ║ 📊 市场数据：
        ║   • 操纵评分: 85/100 ⚠️
        ║   • 入场价格: $2,380
        ║   • 止损价格: $2,451 (+3%)
        ║   • 目标1: $2,261 (-5%)
        ║   • 目标2: $2,142 (-10%)
        ║
        ║ 💡 交易建议：
        ║   • 方向: 做空 📉
        ║   • 仓位: 5-10%
        ║   • 持仓: <1小时
        ║   • 置信度: 87% ✅
        ║
        ║ ⚠️ 风险提示：
        ║   虎口夺食，快进快出！
        ╚════════════════════════════
        """
        direction_emoji = "📉" if signal.direction == "SHORT" else "📈"
        direction_text = "做空" if signal.direction == "SHORT" else "做多"

        strategy_names = {
            'V4A_SHORT': 'V4A 支撑崩塌',
            'V7_SHORT': 'V7 价格OI背离',
            'V8_SHORT': 'V8 插针+OI骤降',
            'LONG': '反弹做多'
        }
        strategy_name = strategy_names.get(signal.strategy, signal.strategy)

        # 计算止盈幅度
        entry = signal.entry_price
        tp1_pct = ((signal.take_profit_1 - entry) / entry) * 100
        tp2_pct = ((signal.take_profit_2 - entry) / entry) * 100 if signal.take_profit_2 else 0
        sl_pct = ((signal.stop_loss - entry) / entry) * 100

        msg = f"""
╔════════════════════════════
║ {'🔴' if signal.direction == 'SHORT' else '🟢'} {direction_text}信号 - {signal.symbol}
║ 策略: {strategy_name}
╠════════════════════════════
║ 📊 市场数据：
║   • 操纵评分: {signal.manipulation_score}/100 {'⚠️' if signal.manipulation_score >= 70 else ''}
║   • 入场价格: ${entry:,.4f}
║   • 止损价格: ${signal.stop_loss:,.4f} ({sl_pct:+.1f}%)
║   • 目标1: ${signal.take_profit_1:,.4f} ({tp1_pct:+.1f}%)"""

        if signal.take_profit_2:
            msg += f"\n║   • 目标2: ${signal.take_profit_2:,.4f} ({tp2_pct:+.1f}%)"

        msg += f"""
║
║ 💡 交易建议：
║   • 方向: {direction_text} {direction_emoji}
║   • 仓位: {signal.position_size}"""

        if signal.max_holding_hours:
            msg += f"\n║   • 持仓: <{signal.max_holding_hours}小时"

        msg += f"""
║   • 置信度: {signal.confidence}% {'✅' if signal.confidence >= 70 else '⚠️'}
║
║ ⚠️ 风险提示：
║   {signal.note}
╚════════════════════════════
        """

        return msg.strip()
