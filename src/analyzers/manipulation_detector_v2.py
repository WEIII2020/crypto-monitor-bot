"""
Manipulation Detector V2 - 妖币检测器（基于 Skanda 研究）

核心逻辑：
1. Binance OI占比中位数越低 → 操纵程度越高
2. vol/OI ≥ 20x → 刷量严重，过滤掉
3. V4A：支撑崩塌策略（早进、短持、快出）
4. V7：价格OI背离（聪明钱撤退）
5. V8：插针+OI骤降（空头真空）
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
import asyncio

from src.database.redis_client import redis_client
from src.utils.logger import logger


@dataclass
class ManipulationScore:
    """操纵评分"""
    symbol: str
    score: int  # 0-100，越高越可能是妖币
    binance_oi_ratio: float  # Binance OI占比（越低越操纵）
    vol_oi_ratio: float  # 成交量/OI比率
    control_rate: float  # 现货控盘率估算
    risk_level: str  # EXTREME, HIGH, MEDIUM, LOW
    signals: List[str]  # 触发的信号列表


class ManipulationDetectorV2:
    """
    妖币检测器 V2

    基于 @thecryptoskanda 的量化研究：
    - 识别高操纵币种
    - 过滤刷量币种
    - 生成 V4A/V7/V8 信号
    """

    def __init__(self):
        # 核心阈值（来自研究）
        self.binance_oi_threshold = 0.4  # Binance OI占比 <40% = 高操纵
        self.vol_oi_filter = 20.0  # vol/OI ≥ 20x = 刷量，过滤
        self.control_rate_threshold = 0.96  # 现货控盘率 >96%

        # V4A 参数（早进策略）
        self.v4a_support_break = 0.02  # 跌破支撑 2%
        self.v4a_sell_pressure = 0.55  # 卖压 >55%（买入比 <45%）
        self.v4a_max_holding_hours = 1  # 最大持仓 1 小时
        self.v4a_trail_stop = 0.03  # 反向反弹 3% 出场

        # V7 参数（价格OI背离）
        self.v7_price_rise_threshold = 0.05  # 价格持续上涨 5%+
        self.v7_oi_decline_threshold = -0.10  # OI 连续下降 10%+
        self.v7_time_window_hours = 4  # 4 小时窗口

        # V8 参数（插针+OI骤降）
        self.v8_wick_threshold = 0.05  # 上影线 >5%
        self.v8_oi_drop_30m = -0.15  # 30分钟内 OI 骤降 15%+
        self.v8_price_drop_threshold = -0.03  # 插针后价格回落 3%+

        # 状态追踪
        self.manipulation_scores = {}  # {symbol: ManipulationScore}
        self.active_signals = {}  # {symbol: List[Signal]}

    async def calculate_manipulation_score(
        self,
        symbol: str,
        market_data: Dict
    ) -> Optional[ManipulationScore]:
        """
        计算操纵评分

        Args:
            symbol: 币种
            market_data: 市场数据（包含 OI、成交量等）

        Returns:
            ManipulationScore 或 None
        """
        try:
            # 1. 获取跨所 OI 数据
            binance_oi = market_data.get('binance_oi', 0)
            total_oi = market_data.get('total_oi', 0)

            if total_oi == 0:
                return None

            binance_oi_ratio = binance_oi / total_oi

            # 2. 计算 vol/OI 比率
            volume_24h = market_data.get('volume_24h', 0)
            vol_oi_ratio = volume_24h / binance_oi if binance_oi > 0 else 999

            # 3. 刷量过滤（硬规则）
            if vol_oi_ratio >= self.vol_oi_filter:
                logger.debug(f"{symbol} 刷量严重 (vol/OI={vol_oi_ratio:.1f}x)，过滤")
                return None

            # 4. 计算操纵评分（0-100）
            score = 0
            signals = []

            # 因子1: Binance OI占比（权重 40%）
            if binance_oi_ratio < 0.2:  # 极低
                score += 40
                signals.append("EXTREME_LOW_BINANCE_OI")
            elif binance_oi_ratio < 0.4:  # 低
                score += 30
                signals.append("LOW_BINANCE_OI")
            elif binance_oi_ratio < 0.6:  # 中等
                score += 15

            # 因子2: vol/OI 比率（权重 20%）
            if vol_oi_ratio < 5:  # 成交量异常低
                score += 20
                signals.append("LOW_VOL_OI")
            elif vol_oi_ratio < 10:
                score += 10

            # 因子3: 价格波动率（权重 20%）
            volatility_24h = market_data.get('volatility_24h', 0)
            if volatility_24h > 0.3:  # 24h 波动 >30%
                score += 20
                signals.append("HIGH_VOLATILITY")
            elif volatility_24h > 0.2:
                score += 10

            # 因子4: 资金费率异常（权重 20%）
            funding_rate = market_data.get('funding_rate', 0)
            if abs(funding_rate) > 0.01:  # |FR| > 1%
                score += 20
                signals.append("EXTREME_FUNDING_RATE")
            elif abs(funding_rate) > 0.005:
                score += 10

            # 5. 估算现货控盘率（简化版）
            # 通过 OI集中度 和 价格操纵程度推测
            control_rate = 0.8 + (1 - binance_oi_ratio) * 0.2  # 简化估算

            # 6. 确定风险等级
            if score >= 70:
                risk_level = "EXTREME"
            elif score >= 50:
                risk_level = "HIGH"
            elif score >= 30:
                risk_level = "MEDIUM"
            else:
                risk_level = "LOW"

            manipulation_score = ManipulationScore(
                symbol=symbol,
                score=score,
                binance_oi_ratio=binance_oi_ratio,
                vol_oi_ratio=vol_oi_ratio,
                control_rate=control_rate,
                risk_level=risk_level,
                signals=signals
            )

            # 缓存评分
            self.manipulation_scores[symbol] = manipulation_score

            return manipulation_score

        except Exception as e:
            logger.error(f"Error calculating manipulation score for {symbol}: {e}")
            return None

    async def detect_v4a_signal(
        self,
        symbol: str,
        realtime_data: Dict,
        manipulation_score: ManipulationScore
    ) -> Optional[Dict]:
        """
        V4A 策略：支撑崩塌做空

        触发条件（ALL）：
        1. 操纵评分 ≥ 50（高风险币种）
        2. 跌破支撑位（基于 1H K线）
        3. 卖压主导（买入比 <45%）
        4. 裸 K 确认（不看量、不看振幅）

        Returns:
            做空信号 或 None
        """
        # 条件1: 操纵评分
        if manipulation_score.score < 50:
            return None

        # 条件2: 跌破支撑
        kline_1h = realtime_data.get('kline_1h')
        if not kline_1h:
            return None

        close_price = kline_1h['close']
        open_price = kline_1h['open']

        # 1H 收阴（close < open）
        if close_price >= open_price:
            return None

        drop_pct = (close_price - open_price) / open_price
        if drop_pct > -self.v4a_support_break:  # 未跌破 2%
            return None

        # 条件3: 卖压主导
        metrics = realtime_data.get('metrics')
        if not metrics:
            return None

        buy_ratio = metrics['buy_ratio']
        if buy_ratio >= (1 - self.v4a_sell_pressure) * 100:  # 买入比 ≥ 45%
            return None

        # ✅ 触发 V4A 做空信号
        signal = {
            'type': 'V4A_SHORT',
            'strategy': 'SUPPORT_COLLAPSE',
            'symbol': symbol,
            'timestamp': datetime.now(),

            # 操纵数据
            'manipulation_score': manipulation_score.score,
            'binance_oi_ratio': manipulation_score.binance_oi_ratio,
            'vol_oi_ratio': manipulation_score.vol_oi_ratio,
            'risk_level': manipulation_score.risk_level,

            # 入场数据
            'entry_price': close_price,
            'support_break': abs(drop_pct) * 100,  # 跌破幅度
            'buy_ratio': buy_ratio,
            'sell_ratio': 100 - buy_ratio,

            # 交易建议
            'action': '轻仓做空',
            'direction': 'SHORT',
            'stop_loss': close_price * (1 + self.v4a_trail_stop),
            'max_holding_hours': self.v4a_max_holding_hours,
            'position_size': '5-10% 仓位',

            # 核心理念
            'note': '早进、短持、快出（V4A 妖币策略）',
            'risk': 'VERY_HIGH - 虎口夺食，严格止损！'
        }

        return signal

    async def detect_v7_signal(
        self,
        symbol: str,
        historical_data: Dict
    ) -> Optional[Dict]:
        """
        V7 策略：聪明钱撤退（价格OI背离）

        触发条件：
        1. 价格持续上涨（4h内 +5%）
        2. OI 连续下降（-10%）
        3. 价格被托涨，但聪明钱在撤退

        Returns:
            做空信号 或 None
        """
        try:
            # 获取 4 小时历史数据
            price_4h_ago = historical_data.get('price_4h_ago')
            oi_4h_ago = historical_data.get('oi_4h_ago')
            current_price = historical_data.get('current_price')
            current_oi = historical_data.get('current_oi')

            if not all([price_4h_ago, oi_4h_ago, current_price, current_oi]):
                return None

            # 计算变化率
            price_change = (current_price - price_4h_ago) / price_4h_ago
            oi_change = (current_oi - oi_4h_ago) / oi_4h_ago

            # 条件1: 价格上涨
            if price_change < self.v7_price_rise_threshold:
                return None

            # 条件2: OI 下降（背离）
            if oi_change > self.v7_oi_decline_threshold:
                return None

            # ✅ 触发 V7 做空信号
            signal = {
                'type': 'V7_SHORT',
                'strategy': 'SMART_MONEY_EXIT',
                'symbol': symbol,
                'timestamp': datetime.now(),

                # 背离数据
                'price_change_4h': price_change * 100,
                'oi_change_4h': oi_change * 100,
                'divergence_strength': abs(price_change - oi_change) * 100,

                # 入场数据
                'entry_price': current_price,

                # 交易建议
                'action': '做空',
                'direction': 'SHORT',
                'stop_loss': current_price * 1.05,  # 止损 +5%
                'take_profit_1': current_price * 0.95,  # 目标 -5%
                'take_profit_2': current_price * 0.90,  # 目标 -10%

                # 核心理念
                'note': '价格托涨，聪明钱撤退，紧跟 trailing 止盈',
                'risk': 'HIGH - 需快速反应'
            }

            return signal

        except Exception as e:
            logger.error(f"Error detecting V7 signal for {symbol}: {e}")
            return None

    async def detect_v8_signal(
        self,
        symbol: str,
        realtime_data: Dict,
        manipulation_score: ManipulationScore
    ) -> Optional[Dict]:
        """
        V8 策略：空头真空（插针+OI骤降）

        触发条件：
        1. 操纵币种（评分 ≥ 50）
        2. 急速插针（上影线 >5%）
        3. 30分钟内 OI 骤降 15%+

        优势：比纯 K线 快 2-4 小时

        Returns:
            做空信号 或 None
        """
        # 条件1: 操纵币种
        if manipulation_score.score < 50:
            return None

        # 条件2: 插针检测
        kline = realtime_data.get('kline_1m')
        if not kline:
            return None

        high = kline['high']
        close = kline['close']
        open_price = kline['open']

        # 计算上影线
        body_top = max(open_price, close)
        upper_wick = (high - body_top) / body_top if body_top > 0 else 0

        if upper_wick < self.v8_wick_threshold:  # 上影线 < 5%
            return None

        # 插针后价格回落
        if close > open_price * (1 - self.v8_price_drop_threshold):
            return None  # 未回落

        # 条件3: 30分钟内 OI 骤降
        oi_30m_ago = realtime_data.get('oi_30m_ago')
        current_oi = realtime_data.get('current_oi')

        if not oi_30m_ago or not current_oi:
            return None

        oi_change_30m = (current_oi - oi_30m_ago) / oi_30m_ago

        if oi_change_30m > self.v8_oi_drop_30m:  # OI 未骤降
            return None

        # ✅ 触发 V8 做空信号
        signal = {
            'type': 'V8_SHORT',
            'strategy': 'LIQUIDATION_VACUUM',
            'symbol': symbol,
            'timestamp': datetime.now(),

            # 插针数据
            'upper_wick_pct': upper_wick * 100,
            'wick_high': high,
            'price_drop': ((close - open_price) / open_price) * 100,

            # OI 数据
            'oi_drop_30m': oi_change_30m * 100,
            'manipulation_score': manipulation_score.score,

            # 入场数据
            'entry_price': close,

            # 交易建议
            'action': '做空',
            'direction': 'SHORT',
            'stop_loss': high * 1.02,  # 止损在上影线上方 2%
            'take_profit_1': close * 0.93,  # 目标 -7%
            'take_profit_2': close * 0.85,  # 目标 -15%

            # 核心理念
            'note': '插针+OI骤降，比纯K线快2-4小时（最强V4A补充）',
            'risk': 'HIGH - 速度是核心'
        }

        return signal

    async def detect_long_signal(
        self,
        symbol: str,
        realtime_data: Dict,
        manipulation_score: ManipulationScore
    ) -> Optional[Dict]:
        """
        做多信号检测（反向逻辑）

        触发条件：
        1. 大跌后反弹（-5%+ 后反弹 >2%）
        2. 买方主导（买入比 >70%）
        3. OI 上升（资金流入）
        4. 非高操纵币种（评分 <70）

        Returns:
            做多信号 或 None
        """
        # 条件1: 非极端操纵币种
        if manipulation_score.score >= 70:
            return None  # 极端操纵币种不做多

        # 条件2: 大跌后反弹
        kline_1h = realtime_data.get('kline_1h')
        if not kline_1h:
            return None

        low_1h = kline_1h['low']
        close = kline_1h['close']
        open_price = kline_1h['open']

        # 检查是否先大跌
        drop_from_open = (low_1h - open_price) / open_price
        if drop_from_open > -0.05:  # 未大跌 5%
            return None

        # 检查是否反弹
        bounce = (close - low_1h) / low_1h
        if bounce < 0.02:  # 反弹不足 2%
            return None

        # 条件3: 买方主导
        metrics = realtime_data.get('metrics')
        if not metrics:
            return None

        buy_ratio = metrics['buy_ratio']
        if buy_ratio < 70:  # 买入比 < 70%
            return None

        # 条件4: OI 上升
        oi_change_1h = realtime_data.get('oi_change_1h', 0)
        if oi_change_1h < 0.05:  # OI 未上升 5%
            return None

        # ✅ 触发做多信号
        signal = {
            'type': 'LONG',
            'strategy': 'BOUNCE_AFTER_DIP',
            'symbol': symbol,
            'timestamp': datetime.now(),

            # 反弹数据
            'drop_from_open': drop_from_open * 100,
            'bounce_from_low': bounce * 100,
            'buy_ratio': buy_ratio,
            'oi_change_1h': oi_change_1h * 100,

            # 入场数据
            'entry_price': close,

            # 交易建议
            'action': '轻仓做多',
            'direction': 'LONG',
            'stop_loss': low_1h * 0.98,  # 止损在低点下方 2%
            'take_profit_1': close * 1.05,  # 目标 +5%
            'take_profit_2': close * 1.08,  # 目标 +8%
            'max_holding_hours': 2,

            # 核心理念
            'note': '大跌后反弹，买方主导，短期做多',
            'risk': 'MEDIUM - 快进快出'
        }

        return signal

    def get_top_manipulation_coins(self, top_n: int = 20) -> List[ManipulationScore]:
        """
        获取操纵评分最高的币种

        Args:
            top_n: 返回前 N 个

        Returns:
            操纵评分列表（按评分降序）
        """
        scores = sorted(
            self.manipulation_scores.values(),
            key=lambda x: x.score,
            reverse=True
        )
        return scores[:top_n]
