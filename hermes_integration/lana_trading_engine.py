"""
Hermes Agent - Lana Trading Engine
基于Lana方法的自动交易引擎
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum


class TradeAction(Enum):
    """交易动作"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class PositionStatus(Enum):
    """持仓状态"""
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    STOPPED = "STOPPED"


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    entry_price: float
    entry_time: datetime
    size: float  # USDT
    stop_loss_price: float
    target_profit_price: Optional[float]
    status: PositionStatus
    pnl: float = 0.0


class LanaRuleEngine:
    """
    Lana交易规则引擎

    核心原则:
    1. 永远不预测启动
    2. 裸K是唯一神
    3. 入场越早越好
    4. 出场必须机械化
    5. 持仓极短(1小时)
    6. 真实成本优先
    7. 选币要动态
    8. 虎口夺食心态
    """

    def __init__(self):
        # Lana规则参数
        self.max_loss_usdt = 200            # 最大亏损200 USDT
        self.max_holding_seconds = 3600      # 最长持仓1小时
        self.min_signal_score = 85           # 最低信号分数
        self.position_size_usdt = 1000       # 标准仓位1000 USDT

        # 当前持仓
        self.positions: Dict[str, Position] = {}

    def check_signal_quality(self, signal: Dict) -> bool:
        """
        检查信号是否符合Lana标准

        Args:
            signal: 融合信号数据
                {
                    'symbol': 'BTC/USDT',
                    'score': 90,
                    'types': ['OI_SPIKE', 'PRICE_SPIKE'],
                    'price': 60000,
                    'action': 'BUY'
                }

        Returns:
            True if 符合标准
        """
        # 规则1: 分数必须≥85分
        if signal.get('score', 0) < self.min_signal_score:
            print(f"❌ 分数不足: {signal.get('score')}分 < {self.min_signal_score}分")
            return False

        # 规则2: 必须包含OI_SPIKE（Lana核心信号）
        signal_types = signal.get('types', [])
        if 'OI_SPIKE' not in signal_types:
            print(f"❌ 缺少OI_SPIKE信号")
            return False

        # 规则3: 必须有明确的行动建议
        action = signal.get('action', '')
        if action not in ['BUY', 'SELL']:
            print(f"❌ 无明确行动建议: {action}")
            return False

        # 规则4: 价格必须已经启动（价格变动>3%）
        price_change = signal.get('price_change', 0)
        if abs(price_change) < 3:
            print(f"❌ 价格未启动: {price_change}% < 3%")
            return False

        print(f"✅ 信号符合Lana标准")
        return True

    def calculate_position_size(self, signal_score: int) -> float:
        """
        根据信号分数计算仓位

        Args:
            signal_score: 信号评分 (0-100)

        Returns:
            仓位大小 (USDT)
        """
        # 基础仓位
        base_size = self.position_size_usdt

        # 根据分数调整
        if signal_score >= 95:
            # 超高分信号，加大仓位
            return base_size * 1.5
        elif signal_score >= 90:
            # 高分信号，标准仓位
            return base_size
        elif signal_score >= 85:
            # 合格信号，减小仓位
            return base_size * 0.7
        else:
            # 不符合标准
            return 0

    def calculate_stop_loss(
        self,
        entry_price: float,
        position_size: float,
        action: TradeAction
    ) -> float:
        """
        计算止损价格（固定亏损200 USDT）

        Args:
            entry_price: 开仓价格
            position_size: 仓位大小 (USDT)
            action: 交易方向

        Returns:
            止损价格
        """
        # 计算损失百分比
        loss_pct = self.max_loss_usdt / position_size

        if action == TradeAction.BUY:
            # 做多: 止损价 = 开仓价 * (1 - 损失%)
            stop_loss = entry_price * (1 - loss_pct)
        else:  # SELL
            # 做空: 止损价 = 开仓价 * (1 + 损失%)
            stop_loss = entry_price * (1 + loss_pct)

        return stop_loss

    def should_enter_trade(self, signal: Dict) -> bool:
        """
        判断是否应该开仓

        Args:
            signal: 融合信号

        Returns:
            True if 应该开仓
        """
        symbol = signal.get('symbol')

        # 检查是否已有持仓
        if symbol in self.positions:
            pos = self.positions[symbol]
            if pos.status == PositionStatus.OPEN:
                print(f"⚠️ {symbol} 已有持仓，不重复开仓")
                return False

        # 检查信号质量
        if not self.check_signal_quality(signal):
            return False

        return True

    def should_exit_trade(
        self,
        position: Position,
        current_price: float,
        current_time: datetime
    ) -> tuple[bool, str]:
        """
        判断是否应该平仓

        Args:
            position: 持仓信息
            current_price: 当前价格
            current_time: 当前时间

        Returns:
            (是否平仓, 原因)
        """
        # 规则1: 触及止损 (最高优先级)
        if current_price <= position.stop_loss_price:
            return True, f"触及止损 (亏损200 USDT)"

        # 规则2: 持仓时间超过1小时 (机械化出场)
        holding_seconds = (current_time - position.entry_time).total_seconds()
        if holding_seconds >= self.max_holding_seconds:
            return True, f"持仓超时 ({holding_seconds/60:.0f}分钟)"

        # 规则3: 达到目标利润（如果有设置）
        if position.target_profit_price:
            if current_price >= position.target_profit_price:
                return True, f"达到目标利润"

        return False, "持仓中"

    def open_position(self, signal: Dict) -> Optional[Position]:
        """
        开仓

        Args:
            signal: 融合信号

        Returns:
            Position对象
        """
        if not self.should_enter_trade(signal):
            return None

        symbol = signal['symbol']
        entry_price = signal['price']
        score = signal['score']
        action = TradeAction[signal['action']]

        # 计算仓位
        position_size = self.calculate_position_size(score)

        # 计算止损
        stop_loss = self.calculate_stop_loss(entry_price, position_size, action)

        # 创建持仓
        position = Position(
            symbol=symbol,
            entry_price=entry_price,
            entry_time=datetime.now(),
            size=position_size,
            stop_loss_price=stop_loss,
            target_profit_price=None,  # Lana不设目标利润
            status=PositionStatus.OPEN
        )

        self.positions[symbol] = position

        print(f"""
🟢 开仓成功

🪙 币种: {symbol}
📊 信号分数: {score}/100
💰 开仓价格: ${entry_price:.4f}
📦 仓位大小: {position_size} USDT
🛑 止损价格: ${stop_loss:.4f}
⏱️ 持仓时间: 最长1小时

⚠️ Lana规则:
  • 亏损200 USDT立即止损
  • 持仓≤1小时强制平仓
  • 严格执行，不做主观判断
        """)

        return position

    def close_position(
        self,
        symbol: str,
        current_price: float,
        reason: str
    ) -> Optional[Position]:
        """
        平仓

        Args:
            symbol: 币种
            current_price: 平仓价格
            reason: 平仓原因

        Returns:
            已平仓的Position对象
        """
        if symbol not in self.positions:
            return None

        position = self.positions[symbol]

        if position.status != PositionStatus.OPEN:
            return None

        # 计算盈亏
        pnl = (current_price - position.entry_price) / position.entry_price * position.size

        # 更新状态
        position.status = PositionStatus.CLOSED
        position.pnl = pnl

        # 判断是否止损
        if "止损" in reason:
            position.status = PositionStatus.STOPPED

        holding_time = (datetime.now() - position.entry_time).total_seconds() / 60

        print(f"""
🔴 平仓完成

🪙 币种: {symbol}
💰 开仓价: ${position.entry_price:.4f}
💰 平仓价: ${current_price:.4f}
📦 仓位: {position.size} USDT
💵 盈亏: {pnl:+.2f} USDT ({pnl/position.size*100:+.2f}%)
⏱️ 持仓时间: {holding_time:.1f}分钟
📝 原因: {reason}

{'✅ 盈利' if pnl > 0 else '❌ 亏损' if pnl < 0 else '➖ 保本'}
        """)

        return position

    def get_position_summary(self) -> Dict:
        """
        获取持仓摘要

        Returns:
            持仓统计数据
        """
        open_positions = [p for p in self.positions.values() if p.status == PositionStatus.OPEN]
        closed_positions = [p for p in self.positions.values() if p.status != PositionStatus.OPEN]

        total_pnl = sum(p.pnl for p in closed_positions)
        win_count = len([p for p in closed_positions if p.pnl > 0])
        loss_count = len([p for p in closed_positions if p.pnl < 0])
        win_rate = win_count / len(closed_positions) * 100 if closed_positions else 0

        return {
            'open_count': len(open_positions),
            'closed_count': len(closed_positions),
            'total_pnl': total_pnl,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': win_rate
        }


class BinanceTradeExecutor:
    """
    Binance交易执行器（模拟）

    实际部署时需要集成真实的Binance API
    """

    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        print(f"🔗 Binance API 已连接 ({'测试网' if testnet else '正式环境'})")

    async def place_market_order(
        self,
        symbol: str,
        side: str,  # BUY or SELL
        quantity: float
    ) -> Dict:
        """
        下市价单（模拟）

        实际实现需要调用Binance API
        """
        print(f"📝 模拟下单: {side} {quantity} {symbol}")

        # 模拟订单
        order = {
            'orderId': 123456,
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': quantity,
            'status': 'FILLED',
            'executedQty': quantity,
            'avgPrice': 60000  # 模拟价格
        }

        return order

    async def place_stop_loss_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float
    ) -> Dict:
        """
        下止损单（模拟）
        """
        print(f"🛑 模拟止损单: {side} {quantity} {symbol} @ ${stop_price}")

        order = {
            'orderId': 123457,
            'symbol': symbol,
            'side': side,
            'type': 'STOP_MARKET',
            'quantity': quantity,
            'stopPrice': stop_price,
            'status': 'NEW'
        }

        return order

    async def get_current_price(self, symbol: str) -> float:
        """获取当前价格（模拟）"""
        # 实际实现需要调用Binance API
        return 60000.0


# 使用示例
async def example_usage():
    """完整交易流程示例"""
    print("=" * 60)
    print("Lana Trading Engine - 使用示例")
    print("=" * 60)

    # 1. 初始化引擎
    engine = LanaRuleEngine()

    # 2. 初始化交易执行器
    executor = BinanceTradeExecutor(
        api_key="your_api_key",
        api_secret="your_api_secret",
        testnet=True
    )

    # 3. 模拟融合信号
    signal = {
        'symbol': 'BTC/USDT',
        'score': 90,
        'types': ['OI_SPIKE', 'PRICE_SPIKE', 'WHALE_ACTIVITY'],
        'price': 60000,
        'price_change': 5.2,
        'action': 'BUY'
    }

    print(f"\n📊 收到融合信号:")
    print(f"   币种: {signal['symbol']}")
    print(f"   分数: {signal['score']}/100")
    print(f"   信号: {', '.join(signal['types'])}")

    # 4. 检查是否开仓
    if engine.should_enter_trade(signal):
        position = engine.open_position(signal)

        if position:
            # 5. 执行开仓（模拟）
            order = await executor.place_market_order(
                symbol=position.symbol,
                side=signal['action'],
                quantity=position.size / position.entry_price
            )

            # 6. 设置止损单（模拟）
            stop_order = await executor.place_stop_loss_order(
                symbol=position.symbol,
                side='SELL' if signal['action'] == 'BUY' else 'BUY',
                quantity=position.size / position.entry_price,
                stop_price=position.stop_loss_price
            )

            # 7. 模拟持仓监控
            print(f"\n⏳ 持仓监控中...")
            await asyncio.sleep(2)

            # 8. 模拟价格变化和平仓检查
            current_price = 60500  # 假设价格上涨
            current_time = datetime.now()

            should_exit, reason = engine.should_exit_trade(
                position,
                current_price,
                current_time
            )

            if should_exit:
                engine.close_position(
                    position.symbol,
                    current_price,
                    reason
                )

    # 9. 获取持仓摘要
    summary = engine.get_position_summary()
    print(f"\n📊 持仓摘要:")
    print(f"   开仓中: {summary['open_count']}个")
    print(f"   已平仓: {summary['closed_count']}个")
    print(f"   总盈亏: {summary['total_pnl']:+.2f} USDT")
    print(f"   胜率: {summary['win_rate']:.1f}%")


if __name__ == "__main__":
    asyncio.run(example_usage())
