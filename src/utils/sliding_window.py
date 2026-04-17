"""
Sliding Window - 高性能滑动窗口数据结构
支持毫秒级查询和实时指标计算
"""

from collections import deque
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np
from dataclasses import dataclass

from src.utils.logger import logger


@dataclass
class Trade:
    """成交记录"""
    price: float
    quantity: float
    timestamp_ms: int
    is_buyer_maker: bool  # True=卖单主动成交, False=买单主动成交
    quote_qty: float  # USDT成交额


class SlidingWindow:
    """
    滑动窗口数据结构

    功能：
    - O(1) 添加成交记录
    - O(n) 计算窗口内指标（n通常<1000，很快）
    - 自动清理过期数据

    使用场景：
    - 实时计算买卖压力
    - 1分钟/5分钟价格变化
    - 成交量异常检测
    """

    def __init__(self, window_seconds: int = 60, max_trades: int = 10000):
        """
        Args:
            window_seconds: 窗口时长（秒），默认60秒
            max_trades: 最大保留成交数，防止内存溢出
        """
        self.window_ms = window_seconds * 1000
        self.trades = deque(maxlen=max_trades)
        self.last_cleanup = 0

        # 统计信息
        self.total_trades = 0
        self.total_buy_volume = 0.0
        self.total_sell_volume = 0.0

    def add_trade(
        self,
        price: float,
        quantity: float,
        timestamp_ms: int,
        is_buyer_maker: bool,
        quote_qty: float = None
    ):
        """
        添加成交记录（O(1)）

        Args:
            price: 成交价格
            quantity: 成交数量（币）
            timestamp_ms: 时间戳（毫秒）
            is_buyer_maker: True=卖单, False=买单
            quote_qty: USDT成交额（可选，会自动计算）
        """
        if quote_qty is None:
            quote_qty = price * quantity

        trade = Trade(
            price=price,
            quantity=quantity,
            timestamp_ms=timestamp_ms,
            is_buyer_maker=is_buyer_maker,
            quote_qty=quote_qty
        )

        self.trades.append(trade)
        self.total_trades += 1

        # 统计买卖量
        if is_buyer_maker:
            self.total_sell_volume += quote_qty
        else:
            self.total_buy_volume += quote_qty

        # 定期清理过期数据（每10秒）
        if timestamp_ms - self.last_cleanup > 10000:
            self._cleanup_old_trades(timestamp_ms)
            self.last_cleanup = timestamp_ms

    def get_metrics(self, now_ms: int = None) -> Optional[Dict]:
        """
        计算窗口内指标（O(n)）

        Args:
            now_ms: 当前时间戳（毫秒），不传则使用系统时间

        Returns:
            指标字典，包含：
            - buy_ratio: 买入占比 (%)
            - sell_ratio: 卖出占比 (%)
            - price_change_pct: 价格变化率 (%)
            - high: 最高价
            - low: 最低价
            - open: 开盘价（窗口内第一笔）
            - close: 收盘价（窗口内最后一笔）
            - volatility: 价格波动率（标准差）
            - trade_count: 成交笔数
            - total_volume: 总成交额（USDT）
            - volume_ratio: 成交量倍数（当前窗口 / 历史平均）
        """
        if now_ms is None:
            now_ms = int(datetime.now().timestamp() * 1000)

        # 过滤窗口内数据
        cutoff = now_ms - self.window_ms
        recent = [t for t in self.trades if t.timestamp_ms >= cutoff]

        if not recent:
            return None

        # 计算买卖量
        buy_volume = sum(t.quote_qty for t in recent if not t.is_buyer_maker)
        sell_volume = sum(t.quote_qty for t in recent if t.is_buyer_maker)
        total_volume = buy_volume + sell_volume

        # 价格数据
        prices = [t.price for t in recent]
        open_price = prices[0]
        close_price = prices[-1]
        high_price = max(prices)
        low_price = min(prices)

        # 计算变化率
        price_change_pct = (close_price - open_price) / open_price * 100 if open_price > 0 else 0

        # 计算波动率
        volatility = float(np.std(prices)) if len(prices) > 1 else 0.0

        # 计算成交量倍数（需要历史数据）
        volume_ratio = self._calculate_volume_ratio(total_volume)

        return {
            'buy_ratio': buy_volume / total_volume * 100 if total_volume > 0 else 50.0,
            'sell_ratio': sell_volume / total_volume * 100 if total_volume > 0 else 50.0,
            'price_change_pct': price_change_pct,
            'high': high_price,
            'low': low_price,
            'open': open_price,
            'close': close_price,
            'volatility': volatility,
            'trade_count': len(recent),
            'total_volume': total_volume,
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'volume_ratio': volume_ratio,
            'avg_price': sum(prices) / len(prices),
            'price_range_pct': (high_price - low_price) / open_price * 100 if open_price > 0 else 0
        }

    def get_large_orders(self, min_usdt: float = 10000, now_ms: int = None) -> List[Dict]:
        """
        获取窗口内的大单（鲸鱼订单）

        Args:
            min_usdt: 最小金额（USDT）
            now_ms: 当前时间戳

        Returns:
            大单列表
        """
        if now_ms is None:
            now_ms = int(datetime.now().timestamp() * 1000)

        cutoff = now_ms - self.window_ms
        large_orders = []

        for t in self.trades:
            if t.timestamp_ms >= cutoff and t.quote_qty >= min_usdt:
                large_orders.append({
                    'price': t.price,
                    'quantity': t.quantity,
                    'quote_qty': t.quote_qty,
                    'timestamp_ms': t.timestamp_ms,
                    'side': 'SELL' if t.is_buyer_maker else 'BUY'
                })

        return sorted(large_orders, key=lambda x: x['quote_qty'], reverse=True)

    def get_price_levels(self, num_levels: int = 10) -> Tuple[List, List]:
        """
        获取价格档位分布（类似盘口）

        Args:
            num_levels: 档位数量

        Returns:
            (买入档位, 卖出档位)
        """
        if not self.trades:
            return [], []

        # 获取价格范围
        prices = [t.price for t in self.trades]
        min_price = min(prices)
        max_price = max(prices)

        # 创建价格档位
        step = (max_price - min_price) / num_levels if max_price > min_price else 0.01

        buy_levels = []
        sell_levels = []

        for i in range(num_levels):
            level_price = min_price + i * step
            level_max = level_price + step

            # 统计该档位的买卖量
            buy_vol = sum(
                t.quote_qty for t in self.trades
                if level_price <= t.price < level_max and not t.is_buyer_maker
            )
            sell_vol = sum(
                t.quote_qty for t in self.trades
                if level_price <= t.price < level_max and t.is_buyer_maker
            )

            if buy_vol > 0:
                buy_levels.append({'price': level_price, 'volume': buy_vol})
            if sell_vol > 0:
                sell_levels.append({'price': level_price, 'volume': sell_vol})

        return buy_levels, sell_levels

    def _cleanup_old_trades(self, now_ms: int):
        """清理过期数据"""
        cutoff = now_ms - self.window_ms * 2  # 保留2倍窗口的数据

        # 从左边移除过期数据
        while self.trades and self.trades[0].timestamp_ms < cutoff:
            self.trades.popleft()

    def _calculate_volume_ratio(self, current_volume: float) -> float:
        """
        计算成交量倍数

        逻辑：当前窗口成交量 / 历史平均成交量
        """
        if self.total_trades < 100:
            return 1.0  # 数据不足，返回1

        # 简单估算：总成交量 / 总笔数 ≈ 平均每笔成交
        # 然后估算一个窗口期内的平均成交量
        avg_per_trade = (self.total_buy_volume + self.total_sell_volume) / self.total_trades

        # 假设平均每秒10笔交易（根据实际调整）
        window_seconds = self.window_ms / 1000
        expected_trades = window_seconds * 10
        expected_volume = avg_per_trade * expected_trades

        if expected_volume > 0:
            return current_volume / expected_volume
        return 1.0

    def get_kline(self, interval_seconds: int = 60, now_ms: int = None) -> Optional[Dict]:
        """
        生成K线数据

        Args:
            interval_seconds: K线周期（秒）
            now_ms: 当前时间戳

        Returns:
            K线数据 {open, high, low, close, volume}
        """
        if now_ms is None:
            now_ms = int(datetime.now().timestamp() * 1000)

        cutoff = now_ms - (interval_seconds * 1000)
        recent = [t for t in self.trades if t.timestamp_ms >= cutoff]

        if not recent:
            return None

        prices = [t.price for t in recent]
        volume = sum(t.quote_qty for t in recent)

        return {
            'open': prices[0],
            'high': max(prices),
            'low': min(prices),
            'close': prices[-1],
            'volume': volume,
            'trade_count': len(recent),
            'start_time': recent[0].timestamp_ms,
            'end_time': recent[-1].timestamp_ms
        }

    def clear(self):
        """清空所有数据"""
        self.trades.clear()
        self.total_trades = 0
        self.total_buy_volume = 0.0
        self.total_sell_volume = 0.0

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'total_trades': self.total_trades,
            'total_buy_volume': self.total_buy_volume,
            'total_sell_volume': self.total_sell_volume,
            'cached_trades': len(self.trades),
            'window_seconds': self.window_ms / 1000
        }
