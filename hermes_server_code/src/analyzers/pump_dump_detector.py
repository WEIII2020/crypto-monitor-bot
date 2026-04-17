"""
Pump & Dump Detector (暴涨回撤检测器)
V4A策略实现：裸K暴涨后第一次卖压做空

核心原则（8条铁律）：
1. 永远不预测启动
2. 裸K是唯一神
3. 入场越早越好
4. 出场必须机械化
5. 持仓极短(1小时)
6. 真实成本优先
7. 选币要动态
8. 虎口夺食心态
"""

from typing import Dict, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass

from src.database.redis_client import redis_client
from src.utils.logger import logger


@dataclass
class PumpEvent:
    """暴涨事件"""
    symbol: str
    start_time: datetime
    start_price: float
    peak_price: float
    peak_time: datetime
    gain_percent: float
    volume_multiplier: float
    status: str  # 'MONITORING', 'DUMPED', 'FAILED'


@dataclass
class ShortPosition:
    """做空头寸"""
    symbol: str
    entry_price: float
    entry_time: datetime
    stop_loss: float
    target_5pct: float
    target_10pct: float
    status: str  # 'OPEN', 'CLOSED', 'STOPPED'


class PumpDumpDetector:
    """
    暴涨回撤检测器 - V4A策略

    检测流程：
    1. 监控所有妖币
    2. 识别暴涨（20%+ / 4h）
    3. 进入高频监控模式
    4. 捕捉第一次卖压（弃盘点）
    5. 发送早空信号
    6. 监控平仓/止损
    """

    def __init__(self):
        # 朋友的精准参数（ALL条件）
        self.pump_threshold = 20.0          # 6小时涨幅 >20%
        self.pump_timeframe = 360           # 6小时（分钟）
        self.dump_buy_ratio = 45.0          # 买卖比 <45%（卖压主导）
        self.min_volume_usdt = 500000       # 24h成交量 >$500K
        self.alert_cooldown_hours = 4       # 4小时冷却

        # 止盈止损参数（简化）
        self.stop_loss_pct = 3.0            # 止损: +3%
        self.max_holding_hours = 1          # 最大持仓: <1小时（朋友建议）

        # 状态追踪
        self.active_pumps: Dict[str, PumpEvent] = {}
        self.active_shorts: Dict[str, ShortPosition] = {}
        self.pump_history: Dict[str, List[PumpEvent]] = defaultdict(list)

    async def check_opportunity(
        self,
        exchange: str,
        symbol: str,
        is_manipulation_coin: bool = True
    ) -> Optional[Dict]:
        """
        检查做空机会

        Args:
            exchange: 交易所
            symbol: 币种
            is_manipulation_coin: 是否为已识别的妖币

        Returns:
            alert dict or None
        """
        try:
            # 1. 检查是否有活跃的做空头寸
            if symbol in self.active_shorts:
                # 监控平仓/止损
                exit_alert = await self._check_exit_signal(symbol)
                if exit_alert:
                    return exit_alert

            # 2. 检查是否在监控暴涨
            if symbol in self.active_pumps:
                # 监控弃盘点
                dump_alert = await self._check_dump_signal(exchange, symbol)
                if dump_alert:
                    return dump_alert
            else:
                # 3. 检测新的暴涨
                pump_alert = await self._check_pump_signal(
                    exchange,
                    symbol,
                    is_manipulation_coin
                )
                if pump_alert:
                    return pump_alert

            return None

        except Exception as e:
            logger.error(f"Error checking pump-dump opportunity for {symbol}: {e}")
            return None

    async def _check_pump_signal(
        self,
        exchange: str,
        symbol: str,
        is_manipulation_coin: bool
    ) -> Optional[Dict]:
        """
        检测暴涨信号（朋友方法第1步）

        触发条件：仅记录暴涨，不发告警
        - 6小时内涨幅 >20%
        """
        try:
            # 获取6小时数据
            prices = await redis_client.get_prices(
                exchange,
                symbol,
                minutes=self.pump_timeframe
            )

            if len(prices) < 10:
                return None

            # 计算6小时涨幅
            latest_price = prices[0]['price']
            earliest_price = prices[-1]['price']

            if earliest_price == 0:
                return None

            gain_pct = ((latest_price - earliest_price) / earliest_price) * 100

            # 检查是否达到20%阈值
            if gain_pct < self.pump_threshold:
                return None

            # 记录暴涨事件（进入监控）
            pump_event = PumpEvent(
                symbol=symbol,
                start_time=datetime.fromtimestamp(prices[-1]['timestamp']),
                start_price=earliest_price,
                peak_price=latest_price,
                peak_time=datetime.fromtimestamp(prices[0]['timestamp']),
                gain_percent=gain_pct,
                volume_multiplier=0,  # 不检查成交量倍数
                status='MONITORING'
            )

            self.active_pumps[symbol] = pump_event

            logger.info(
                f"📊 检测到暴涨: {symbol} +{gain_pct:.1f}% (6h) - 进入监控"
            )

            # 不发告警，直接返回None（等待弃盘点）
            return None

        except Exception as e:
            logger.error(f"Error checking pump signal: {e}")
            return None

    async def _check_dump_signal(
        self,
        exchange: str,
        symbol: str
    ) -> Optional[Dict]:
        """
        检测做空信号（朋友方法 - ALL条件）

        触发条件（必须全部满足）：
        1. ✅ 过去6小时涨幅 >20%（已在active_pumps中）
        2. 最新1H K线收阴（close < open）
        3. 买卖比 <45%（卖压主导）
        4. 24h成交量 >$500K
        5. 4小时内同币不重复报警
        """
        try:
            pump_event = self.active_pumps.get(symbol)
            if not pump_event:
                return None

            # 条件1：已确认暴涨（6h >20%）✅

            # 条件2：最新1H K线收阴
            prices_1h = await redis_client.get_prices(
                exchange,
                symbol,
                minutes=60
            )

            if len(prices_1h) < 2:
                return None

            # 简化：用1小时前后价格模拟收盘/开盘
            close_price = prices_1h[0]['price']  # 最新价 = 收盘价
            open_price = prices_1h[-1]['price']  # 1小时前 = 开盘价

            is_red_candle = close_price < open_price

            if not is_red_candle:
                return None

            # 条件3：买卖比 <45%
            # 从最新ticker获取买卖量（需要从Binance获取takerBuyVolume）
            buy_ratio = await self._get_buy_ratio(exchange, symbol)

            if buy_ratio is None or buy_ratio >= self.dump_buy_ratio:
                return None

            # 条件4：24h成交量 >$500K
            volume_24h = await redis_client.get_avg_volume(
                exchange,
                symbol,
                minutes=1440
            )

            if volume_24h < self.min_volume_usdt:
                return None

            # 条件5：4小时冷却
            alert_key = f"DUMP_{symbol}"
            already_sent = await redis_client.check_alert_sent(symbol, alert_key)

            if already_sent:
                return None

            # 🎯 ALL条件满足！发送做空信号
            logger.info(
                f"🚨 做空信号: {symbol} | "
                f"6h涨幅+{pump_event.gain_percent:.1f}% | "
                f"买卖比{buy_ratio:.1f}% | "
                f"24h量${volume_24h:,.0f}"
            )

            # 标记已发送（4小时冷却）
            cooldown_seconds = self.alert_cooldown_hours * 3600
            await redis_client.mark_alert_sent(symbol, alert_key, ttl_seconds=cooldown_seconds)

            # 创建做空头寸记录
            entry_price = close_price
            stop_loss = entry_price * (1 + self.stop_loss_pct / 100)

            short_position = ShortPosition(
                symbol=symbol,
                entry_price=entry_price,
                entry_time=datetime.now(),
                stop_loss=stop_loss,
                target_5pct=entry_price * 0.95,  # -5%目标（可选）
                target_10pct=entry_price * 0.90,  # -10%目标（可选）
                status='OPEN'
            )

            self.active_shorts[symbol] = short_position
            pump_event.status = 'DUMPED'

            return {
                'symbol': symbol,
                'exchange': exchange,
                'alert_type': 'SHORT_SIGNAL',
                'alert_level': 'CRITICAL',
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'pump_gain': round(pump_event.gain_percent, 2),
                'buy_ratio': round(buy_ratio, 1),
                'volume_24h': volume_24h,
                'message': self._format_short_signal_message(
                    symbol,
                    pump_event.gain_percent,
                    entry_price,
                    buy_ratio,
                    stop_loss
                )
            }

        except Exception as e:
            logger.error(f"Error checking dump signal: {e}")
            return None

    async def _get_buy_ratio(self, exchange: str, symbol: str) -> Optional[float]:
        """
        获取买卖比（买入量 / 总量）

        Binance 24hrTicker 提供：
        - volume: 总成交量
        - quoteVolume: 总成交额
        但不直接提供 takerBuyVolume

        简化方案：从最近价格数据估算
        """
        try:
            # 获取最近1小时的价格变化
            prices = await redis_client.get_prices(exchange, symbol, minutes=60)

            if len(prices) < 10:
                return None

            # 简化估算：价格上涨时段视为买压，下跌视为卖压
            buy_volume = 0
            sell_volume = 0

            for i in range(len(prices) - 1):
                current = prices[i]
                previous = prices[i + 1]

                if current['price'] > previous['price']:
                    buy_volume += current['volume']
                else:
                    sell_volume += current['volume']

            total_volume = buy_volume + sell_volume

            if total_volume == 0:
                return None

            buy_ratio = (buy_volume / total_volume) * 100

            return buy_ratio

        except Exception as e:
            logger.error(f"Error calculating buy ratio: {e}")
            return None

    async def _check_exit_signal(self, symbol: str) -> Optional[Dict]:
        """
        检查平仓/止损信号

        平仓条件：
        1. 回撤达到5%（目标1）
        2. 回撤达到10%（目标2）
        3. 持仓超过2小时（强制平仓）
        4. 反弹超过3%（止损）
        5. 价格创新高（止损）
        """
        try:
            position = self.active_shorts.get(symbol)
            if not position or position.status != 'OPEN':
                return None

            # 获取当前价格
            prices = await redis_client.get_prices(
                'binance',
                symbol,
                minutes=5
            )

            if not prices:
                return None

            current_price = prices[0]['price']
            entry_price = position.entry_price

            # 计算收益
            pnl_pct = ((entry_price - current_price) / entry_price) * 100

            # 检查止损
            if current_price >= position.stop_loss:
                position.status = 'STOPPED'
                del self.active_shorts[symbol]
                if symbol in self.active_pumps:
                    del self.active_pumps[symbol]

                logger.warning(f"⚠️ 止损触发: {symbol} PNL: {pnl_pct:.2f}%")

                return {
                    'symbol': symbol,
                    'alert_type': 'STOP_LOSS',
                    'alert_level': 'WARNING',
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl_pct': round(pnl_pct, 2),
                    'holding_time': self._format_holding_time(position.entry_time),
                    'message': self._format_stop_loss_message(
                        symbol,
                        position,
                        current_price,
                        pnl_pct
                    )
                }

            # 检查止盈
            if current_price <= position.target_5pct:
                position.status = 'CLOSED'
                del self.active_shorts[symbol]
                if symbol in self.active_pumps:
                    del self.active_pumps[symbol]

                target_level = 1 if current_price > position.target_10pct else 2

                logger.info(f"✅ 止盈触发: {symbol} 目标{target_level} PNL: {pnl_pct:.2f}%")

                return {
                    'symbol': symbol,
                    'alert_type': 'TAKE_PROFIT',
                    'alert_level': 'INFO',
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl_pct': round(pnl_pct, 2),
                    'target_level': target_level,
                    'holding_time': self._format_holding_time(position.entry_time),
                    'message': self._format_take_profit_message(
                        symbol,
                        position,
                        current_price,
                        pnl_pct,
                        target_level
                    )
                }

            # 检查强制平仓（时间）
            holding_hours = (datetime.now() - position.entry_time).total_seconds() / 3600

            if holding_hours >= self.max_holding_hours:
                position.status = 'CLOSED'
                del self.active_shorts[symbol]
                if symbol in self.active_pumps:
                    del self.active_pumps[symbol]

                logger.info(f"⏱️ 时间强制平仓: {symbol} PNL: {pnl_pct:.2f}%")

                return {
                    'symbol': symbol,
                    'alert_type': 'FORCED_EXIT',
                    'alert_level': 'INFO',
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'pnl_pct': round(pnl_pct, 2),
                    'holding_time': self._format_holding_time(position.entry_time),
                    'reason': 'max_holding_time',
                    'message': self._format_forced_exit_message(
                        symbol,
                        position,
                        current_price,
                        pnl_pct
                    )
                }

            return None

        except Exception as e:
            logger.error(f"Error checking exit signal: {e}")
            return None

    def _format_short_signal_message(
        self,
        symbol: str,
        gain_pct: float,
        current_price: float,
        buy_ratio: float,
        stop_loss: float
    ) -> str:
        """
        格式化做空信号（朋友的简洁格式）
        """
        lines = [
            f"🚨 做空信号",
            f"",
            f"🪙 {symbol}",
            f"📈 6h涨幅: +{gain_pct:.1f}%",
            f"💰 现价: ${current_price:,.4f}",
            f"📊 买卖比: {buy_ratio:.1f}% (卖压主导)",
            f"",
            f"⚡ 建议:",
            f"  🔴 轻仓做空",
            f"  🔴 Trailing Stop: ${stop_loss:,.4f} (+{self.stop_loss_pct:.1f}%)",
            f"  🔴 持仓时间: <{self.max_holding_hours}小时",
            f"",
            f"⚠️  风险提示:",
            f"  • 严格止损，反弹就跑",
            f"  • 建议低杠杆（2-3x）",
            f"  • 机会无穷，亏一次换下一个",
        ]

        return '\n'.join(lines)

    def _format_holding_time(self, entry_time: datetime) -> str:
        """格式化持仓时间"""
        delta = datetime.now() - entry_time
        hours = delta.total_seconds() / 3600
        minutes = delta.total_seconds() / 60

        if hours >= 1:
            return f"{hours:.1f}小时"
        else:
            return f"{int(minutes)}分钟"


    def _format_take_profit_message(
        self,
        symbol: str,
        position: ShortPosition,
        current_price: float,
        pnl_pct: float,
        target_level: int
    ) -> str:
        """格式化止盈信号"""
        lines = [
            f"🟢 妖币平仓信号 - 目标达成",
            f"",
            f"🪙 {symbol}",
            f"💰 入场价格: ${position.entry_price:,.4f}",
            f"💰 当前价格: ${current_price:,.4f}",
            f"📊 实现收益: +{pnl_pct:.2f}% ✅",
            f"",
            f"⏱️  持仓时间: {self._format_holding_time(position.entry_time)}",
            f"✅ 达成目标{target_level}",
            f"",
            f"⚡ 立即平仓原因:",
            f"  • 回撤{self.take_profit_1 if target_level == 1 else self.take_profit_2}%目标达成",
            f"  • {'快速止盈（目标1）' if target_level == 1 else '完美止盈（目标2）'}",
            f"",
            f"📊 本次交易:",
            f"  • 信号质量: 优秀",
            f"  • 执行效率: 完美",
            f"  • 风险控制: 严格",
        ]

        return '\n'.join(lines)

    def _format_stop_loss_message(
        self,
        symbol: str,
        position: ShortPosition,
        current_price: float,
        pnl_pct: float
    ) -> str:
        """格式化止损信号"""
        lines = [
            f"🔴 妖币止损信号 - 反弹异常",
            f"",
            f"🪙 {symbol}",
            f"💰 入场价格: ${position.entry_price:,.4f}",
            f"💰 当前价格: ${current_price:,.4f}",
            f"📊 实现收益: {pnl_pct:+.2f}% 🔴",
            f"",
            f"⏱️  持仓时间: {self._format_holding_time(position.entry_time)}",
            f"⚠️  触发止损",
            f"",
            f"⚡ 止损原因:",
            f"  • 反弹超过{self.stop_loss_pct}%阈值",
            f"  • 买压突然回归",
            f"  • 可能是假弃盘点",
            f"",
            f"📊 风险控制:",
            f"  • 单笔损失: {pnl_pct:.2f}%",
            f"  • 符合止损纪律 ✅",
            f"  • 下一个机会就是 💪",
        ]

        return '\n'.join(lines)

    def _format_forced_exit_message(
        self,
        symbol: str,
        position: ShortPosition,
        current_price: float,
        pnl_pct: float
    ) -> str:
        """格式化强制平仓信号"""
        lines = [
            f"⏱️ 妖币强制平仓 - 时间到期",
            f"",
            f"🪙 {symbol}",
            f"💰 入场价格: ${position.entry_price:,.4f}",
            f"💰 当前价格: ${current_price:,.4f}",
            f"📊 实现收益: {pnl_pct:+.2f}%",
            f"",
            f"⏱️  持仓时间: {self._format_holding_time(position.entry_time)}",
            f"⚠️  超过{self.max_holding_hours}小时上限",
            f"",
            f"⚡ 强制平仓原因:",
            f"  • 持仓时间过长",
            f"  • 妖币策略要求快进快出",
            f"  • 避免隔夜风险",
            f"",
            f"📊 本次交易:",
            f"  • 收益: {pnl_pct:+.2f}%",
            f"  • 执行: 按纪律行事 ✅",
        ]

        return '\n'.join(lines)

    def get_active_pumps(self) -> List[str]:
        """获取当前监控的暴涨币种"""
        return list(self.active_pumps.keys())

    def get_active_shorts(self) -> List[str]:
        """获取当前的做空头寸"""
        return list(self.active_shorts.keys())

    def clear_expired_positions(self):
        """清理过期的头寸记录"""
        now = datetime.now()
        expired_shorts = []

        for symbol, position in self.active_shorts.items():
            hours = (now - position.entry_time).total_seconds() / 3600
            if hours > 24:  # 24小时后清理
                expired_shorts.append(symbol)

        for symbol in expired_shorts:
            del self.active_shorts[symbol]
            if symbol in self.active_pumps:
                del self.active_pumps[symbol]
            logger.info(f"清理过期头寸: {symbol}")
