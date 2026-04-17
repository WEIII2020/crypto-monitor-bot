"""
Binance Realtime Collector - 毫秒级实时数据采集器
使用 aggTrade WebSocket 流，获取逐笔成交数据
"""

import json
import asyncio
from typing import List, Dict, Optional, Set
from datetime import datetime
import websockets

from src.collectors.base_collector import BaseCollector
from src.database.redis_client import redis_client
from src.utils.logger import logger
from src.utils.sliding_window import SlidingWindow


class BinanceRealtimeCollector(BaseCollector):
    """
    Binance 实时数据采集器（毫秒级）

    数据源：aggTrade（聚合成交）
    延迟：10-50ms

    优势：
    - 每笔成交实时推送
    - 包含买卖方向（主动买/卖）
    - 可自行计算任意周期K线
    """

    def __init__(self):
        super().__init__('binance_realtime')
        self.ws_url = 'wss://stream.binance.com:9443/stream'
        self.ws: Optional[websockets.WebSocketClientProtocol] = None

        # 为每个币种维护滑动窗口
        self.windows: Dict[str, SlidingWindow] = {}

        # 支持多窗口（1分钟、5分钟、15分钟、1小时）
        self.window_configs = {
            '1m': 60,
            '5m': 300,
            '15m': 900,
            '1h': 3600
        }

        # 性能统计
        self.stats = {
            'total_trades': 0,
            'trades_per_second': 0,
            'avg_latency_ms': 0,
            'last_trade_time': None
        }

        # 批量写入缓冲（提升性能）
        self.write_buffer = []
        self.buffer_size = 100

        # 回调函数（可选）
        self.on_price_update = None

    async def connect(self):
        """连接到 Binance WebSocket"""
        try:
            self.ws = await websockets.connect(self.ws_url)
            self.connected = True
            logger.info(f"✅ Connected to Binance Realtime WebSocket")
        except Exception as e:
            logger.error(f"❌ Failed to connect: {e}")
            raise

    async def disconnect(self):
        """断开连接"""
        if self.ws:
            await self.ws.close()
            self.connected = False
            logger.info("Disconnected from Binance Realtime WebSocket")

    def normalize_symbol(self, symbol: str) -> str:
        """BTCUSDT -> BTC/USDT"""
        quote_currencies = ['USDT', 'USDC', 'BUSD', 'BTC', 'ETH', 'BNB']
        for quote in quote_currencies:
            if symbol.endswith(quote):
                base = symbol[:-len(quote)]
                return f"{base}/{quote}"
        return symbol

    def denormalize_symbol(self, symbol: str) -> str:
        """BTC/USDT -> btcusdt"""
        return symbol.replace('/', '').lower()

    async def subscribe_symbols(self, symbols: List[str]):
        """
        订阅币种的实时成交流

        注意：Binance限制每个连接最多1024个stream
        对于200个币种，需要分批连接
        """
        if not self.connected or not self.ws:
            raise ConnectionError("WebSocket not connected")

        # 为每个币种创建滑动窗口
        for symbol in symbols:
            self.windows[symbol] = SlidingWindow(window_seconds=60)

        # 创建订阅消息
        # 格式：btcusdt@aggTrade
        streams = [f"{self.denormalize_symbol(symbol)}@aggTrade" for symbol in symbols]

        # Binance限制：每个连接最多1024个stream
        # 200个币种 < 1024，可以一次性订阅
        if len(streams) > 1024:
            logger.warning(f"⚠️ Too many streams ({len(streams)}), will use multiple connections")
            # TODO: 实现多连接逻辑
            streams = streams[:1024]

        message = {
            'method': 'SUBSCRIBE',
            'params': streams,
            'id': 1
        }

        await self.ws.send(json.dumps(message))
        self.subscribed_symbols = symbols

        logger.info(f"✅ Subscribed to {len(symbols)} symbols (aggTrade stream)")

    async def handle_message(self, message: Dict):
        """
        处理实时成交消息

        aggTrade message format:
        {
            "stream": "btcusdt@aggTrade",
            "data": {
                "e": "aggTrade",
                "E": 1672515782136,  # Event time (ms)
                "s": "BTCUSDT",
                "a": 12345,          # Aggregate trade ID
                "p": "40000.00",     # Price
                "q": "0.5",          # Quantity
                "f": 100,            # First trade ID
                "l": 110,            # Last trade ID
                "T": 1672515782134,  # Trade time (ms)
                "m": false           # Is buyer maker (true=sell, false=buy)
            }
        }
        """
        try:
            # 跳过订阅确认消息
            if 'result' in message or 'id' in message:
                return

            # 提取数据
            stream = message.get('stream', '')
            data = message.get('data', {})

            if not data or data.get('e') != 'aggTrade':
                return

            # 解析成交数据
            symbol = self.normalize_symbol(data['s'])
            price = float(data['p'])
            quantity = float(data['q'])
            timestamp_ms = int(data['T'])
            is_buyer_maker = data['m']  # True=卖单主动, False=买单主动

            # 计算延迟（毫秒）
            now_ms = int(datetime.now().timestamp() * 1000)
            latency_ms = now_ms - timestamp_ms

            # 更新统计
            self.stats['total_trades'] += 1
            self.stats['last_trade_time'] = now_ms
            self.stats['avg_latency_ms'] = (
                self.stats['avg_latency_ms'] * 0.9 + latency_ms * 0.1
            )  # 移动平均

            # 添加到滑动窗口
            if symbol in self.windows:
                quote_qty = price * quantity
                self.windows[symbol].add_trade(
                    price=price,
                    quantity=quantity,
                    timestamp_ms=timestamp_ms,
                    is_buyer_maker=is_buyer_maker,
                    quote_qty=quote_qty
                )

            # 准备价格数据（兼容现有系统）
            price_data = {
                'symbol': symbol,
                'price': price,
                'quantity': quantity,
                'timestamp': timestamp_ms / 1000,  # 转为秒
                'timestamp_ms': timestamp_ms,
                'exchange': self.exchange,
                'is_buyer_maker': is_buyer_maker,
                'quote_qty': price * quantity,
                'latency_ms': latency_ms
            }

            # 触发回调
            if self.on_price_update:
                await self.on_price_update(price_data)

            # 存储到 Redis（批量）
            self.write_buffer.append(price_data)
            if len(self.write_buffer) >= self.buffer_size:
                await self._flush_buffer()

        except Exception as e:
            logger.error(f"Error handling message: {e}")

    async def _flush_buffer(self):
        """批量写入 Redis"""
        if not self.write_buffer:
            return

        try:
            # 按币种分组
            grouped = {}
            for data in self.write_buffer:
                symbol = data['symbol']
                if symbol not in grouped:
                    grouped[symbol] = []
                grouped[symbol].append(data)

            # 批量写入
            for symbol, trades in grouped.items():
                key = f"realtime:{self.exchange}:{symbol}"

                # 只保存最新的一笔（节省内存）
                latest = trades[-1]
                await redis_client.set(
                    key,
                    json.dumps(latest),
                    ex=60  # 1分钟过期
                )

            # 清空缓冲
            self.write_buffer.clear()

        except Exception as e:
            logger.error(f"Error flushing buffer: {e}")

    async def get_realtime_metrics(self, symbol: str, window: str = '1m') -> Optional[Dict]:
        """
        获取实时指标

        Args:
            symbol: 币种（BTC/USDT）
            window: 窗口大小（1m, 5m, 15m）

        Returns:
            实时指标字典
        """
        if symbol not in self.windows:
            return None

        window_seconds = self.window_configs.get(window, 60)

        # 临时创建窗口（或缓存多个窗口）
        # 简化实现：直接从主窗口计算
        now_ms = int(datetime.now().timestamp() * 1000)

        return self.windows[symbol].get_metrics(now_ms)

    async def get_large_orders(self, symbol: str, min_usdt: float = 10000) -> List[Dict]:
        """获取大单"""
        if symbol not in self.windows:
            return []

        return self.windows[symbol].get_large_orders(min_usdt)

    async def get_kline(self, symbol: str, interval: str = '1m') -> Optional[Dict]:
        """
        实时生成K线

        Args:
            symbol: 币种
            interval: 周期（1m, 5m, 15m）

        Returns:
            K线数据
        """
        if symbol not in self.windows:
            return None

        interval_seconds = self.window_configs.get(interval, 60)
        return self.windows[symbol].get_kline(interval_seconds)

    async def listen(self):
        """监听 WebSocket 消息"""
        if not self.connected or not self.ws:
            raise ConnectionError("WebSocket not connected")

        logger.info("🎧 Listening for realtime trades...")

        try:
            async for raw_message in self.ws:
                try:
                    message = json.loads(raw_message)
                    await self.handle_message(message)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON decode error: {e}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

        except websockets.exceptions.ConnectionClosed:
            logger.warning("⚠️ WebSocket connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"❌ Error in listen loop: {e}")
            raise

    def get_performance_stats(self) -> Dict:
        """获取性能统计"""
        # 计算每秒交易数
        if self.stats['last_trade_time']:
            now_ms = int(datetime.now().timestamp() * 1000)
            elapsed_seconds = (now_ms - self.stats.get('start_time', now_ms)) / 1000
            if elapsed_seconds > 0:
                self.stats['trades_per_second'] = self.stats['total_trades'] / elapsed_seconds

        return {
            'total_trades': self.stats['total_trades'],
            'trades_per_second': round(self.stats['trades_per_second'], 2),
            'avg_latency_ms': round(self.stats['avg_latency_ms'], 2),
            'active_symbols': len(self.windows),
            'buffer_size': len(self.write_buffer)
        }

    async def connect_with_retry(self, max_retries: int = 5) -> bool:
        """带重试的连接"""
        for attempt in range(max_retries):
            try:
                await self.connect()
                self.stats['start_time'] = int(datetime.now().timestamp() * 1000)
                return True
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1}/{max_retries} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # 指数退避

        return False
