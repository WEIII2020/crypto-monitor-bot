#!/usr/bin/env python3
"""
Crypto Monitor Bot - Phase 2
交易信号生成系统（做多/做空 + 妖币策略）

功能：
- Phase 1: 毫秒级实时数据采集
- Phase 2: V4A/V7/V8 妖币策略 + 做多/做空双向信号
- 自动 Telegram 推送
"""

import asyncio
import signal
import sys
from typing import Set, Dict
from datetime import datetime, timedelta

from src.utils.logger import logger
from src.utils.symbol_selector import SymbolSelector
from src.database.redis_client import redis_client
from src.database.postgres import postgres_client
from src.collectors.binance_realtime_collector import BinanceRealtimeCollector
from src.analyzers.trading_signal_generator import TradingSignalGenerator
from src.notifiers.telegram_notifier import TelegramNotifier


class CryptoMonitorBotPhase2:
    """Phase 2 交易信号系统"""

    def __init__(self):
        self.running = False
        self.tasks: Set[asyncio.Task] = set()

        # Phase 1 组件
        self.collector = BinanceRealtimeCollector()
        self.symbol_selector = SymbolSelector()

        # Phase 2 组件
        self.signal_generator = TradingSignalGenerator()
        self.notifier = TelegramNotifier()

        # 监控配置
        self.test_mode = False  # False = 200币种，True = 5币种测试
        self.symbols = []

        # 历史数据缓存（用于 V7 等策略）
        self.price_history = {}  # {symbol: [(timestamp, price), ...]}
        self.oi_history = {}     # {symbol: [(timestamp, oi), ...]}

        # 性能统计
        self.stats = {
            'total_signals': 0,
            'v4a_signals': 0,
            'v7_signals': 0,
            'v8_signals': 0,
            'long_signals': 0,
            'signals_sent': 0
        }

    async def start(self):
        """启动 Phase 2 系统"""
        logger.info("🚀 Starting Phase 2 Trading Signal System...")

        try:
            # 连接数据库
            await redis_client.connect()
            await postgres_client.connect()
            logger.info("✅ Database connections established")

            # 选择监控币种
            if self.test_mode:
                self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
                logger.info(f"🧪 Test mode: monitoring {len(self.symbols)} symbols")
            else:
                logger.info("📊 Selecting optimal symbols...")
                self.symbols = await self.symbol_selector.get_monitoring_list(max_symbols=200)
                logger.info(f"✅ Selected {len(self.symbols)} symbols")

            # 连接 Binance
            success = await self.collector.connect_with_retry()
            if not success:
                logger.error("❌ Failed to connect to Binance")
                return

            # 订阅实时数据
            await self.collector.subscribe_symbols(self.symbols)
            logger.info(f"✅ Subscribed to {len(self.symbols)} symbols")

            self.running = True

            # 启动后台任务
            collector_task = asyncio.create_task(self._run_collector())
            signal_task = asyncio.create_task(self._run_signal_generation())
            stats_task = asyncio.create_task(self._run_stats_monitor())

            self.tasks.add(collector_task)
            self.tasks.add(signal_task)
            self.tasks.add(stats_task)

            logger.info("✅ Phase 2 system is running! Press Ctrl+C to stop.")

            await asyncio.gather(*self.tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"❌ Error starting Phase 2: {e}")
            await self.stop()

    async def stop(self):
        """停止系统"""
        logger.info("🛑 Stopping Phase 2 system...")
        self.running = False

        for task in self.tasks:
            if not task.done():
                task.cancel()

        await self.collector.disconnect()
        await redis_client.disconnect()
        await postgres_client.disconnect()

        logger.info("✅ Phase 2 stopped successfully")

    async def _run_collector(self):
        """运行数据采集器"""
        try:
            await self.collector.listen()
        except asyncio.CancelledError:
            logger.info("Collector task cancelled")
        except Exception as e:
            logger.error(f"Collector error: {e}")

    async def _run_signal_generation(self):
        """信号生成主循环"""
        logger.info("🔍 Starting signal generation...")

        check_interval = 5  # 每 5 秒检查一次（比 Phase 1 更慢，因为要做深度分析）

        try:
            while self.running:
                for symbol in self.symbols:
                    try:
                        await self._check_trading_signals(symbol)
                    except Exception as e:
                        logger.error(f"Error checking {symbol}: {e}")

                await asyncio.sleep(check_interval)

        except asyncio.CancelledError:
            logger.info("Signal generation task cancelled")
        except Exception as e:
            logger.error(f"Signal generation error: {e}")

    async def _check_trading_signals(self, symbol: str):
        """检查交易信号"""
        try:
            # 1. 获取实时数据（Phase 1）
            realtime_data = await self._get_realtime_data(symbol)
            if not realtime_data:
                return

            # 2. 获取历史数据（用于 V7 等）
            historical_data = await self._get_historical_data(symbol)

            # 3. 获取市场数据（OI、资金费率等）
            market_data = await self._get_market_data(symbol)

            # 4. 生成信号
            signals = await self.signal_generator.generate_signals(
                symbol,
                realtime_data,
                historical_data,
                market_data
            )

            # 5. 处理信号
            for signal in signals:
                await self._handle_signal(signal)

        except Exception as e:
            logger.error(f"Error checking signals for {symbol}: {e}")

    async def _get_realtime_data(self, symbol: str) -> Dict:
        """获取实时数据（Phase 1 提供）"""
        # 从 Phase 1 的滑动窗口获取
        metrics_1m = await self.collector.get_realtime_metrics(symbol, '1m')
        kline_1m = await self.collector.get_kline(symbol, '1m')
        kline_1h = await self.collector.get_kline(symbol, '1h')

        return {
            'metrics': metrics_1m,
            'kline_1m': kline_1m,
            'kline_1h': kline_1h
        }

    async def _get_historical_data(self, symbol: str) -> Dict:
        """获取历史数据"""
        # 从缓存获取 4 小时前的数据
        now = datetime.now()
        four_hours_ago = now - timedelta(hours=4)

        # 简化实现：从 Redis 获取
        # 实际应该从数据库或 API 获取
        price_4h_ago = await self._get_cached_price(symbol, four_hours_ago)
        oi_4h_ago = await self._get_cached_oi(symbol, four_hours_ago)

        current_metrics = await self.collector.get_realtime_metrics(symbol, '1m')
        current_price = current_metrics['close'] if current_metrics else None

        return {
            'price_4h_ago': price_4h_ago,
            'oi_4h_ago': oi_4h_ago,
            'current_price': current_price,
            'current_oi': None  # TODO: 从 API 获取当前 OI
        }

    async def _get_market_data(self, symbol: str) -> Dict:
        """获取市场数据（OI、资金费率等）"""
        # TODO: 从 Coinglass 或 Binance API 获取
        # 当前返回模拟数据
        return {
            'binance_oi': 100000000,  # $100M
            'total_oi': 200000000,    # $200M
            'volume_24h': 500000000,  # $500M
            'volatility_24h': 0.15,   # 15%
            'funding_rate': 0.0001,   # 0.01%
        }

    async def _get_cached_price(self, symbol: str, timestamp: datetime) -> float:
        """从缓存获取历史价格"""
        # 简化实现
        if symbol not in self.price_history:
            return None

        # 查找最接近的价格
        for ts, price in reversed(self.price_history[symbol]):
            if ts <= timestamp:
                return price

        return None

    async def _get_cached_oi(self, symbol: str, timestamp: datetime) -> float:
        """从缓存获取历史 OI"""
        # 简化实现
        if symbol not in self.oi_history:
            return None

        for ts, oi in reversed(self.oi_history[symbol]):
            if ts <= timestamp:
                return oi

        return None

    async def _handle_signal(self, signal):
        """处理信号"""
        # 更新统计
        self.stats['total_signals'] += 1

        if signal.strategy == 'V4A_SHORT':
            self.stats['v4a_signals'] += 1
        elif signal.strategy == 'V7_SHORT':
            self.stats['v7_signals'] += 1
        elif signal.strategy == 'V8_SHORT':
            self.stats['v8_signals'] += 1
        elif signal.strategy == 'LONG':
            self.stats['long_signals'] += 1

        # 格式化消息
        message = self.signal_generator.format_telegram_message(signal)

        # 日志输出
        logger.warning(f"\n{'='*50}")
        logger.warning(f"🎯 NEW SIGNAL: {signal.symbol} - {signal.strategy}")
        logger.warning(message)
        logger.warning(f"{'='*50}\n")

        # 发送 Telegram 通知
        try:
            await self.notifier.send_message(message)
            self.stats['signals_sent'] += 1
            logger.info(f"✅ Signal sent to Telegram: {signal.symbol}")
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram: {e}")

    async def _run_stats_monitor(self):
        """性能监控"""
        logger.info("📈 Starting stats monitor...")

        interval = 60  # 每 60 秒报告一次

        try:
            while self.running:
                await asyncio.sleep(interval)

                # 获取 Phase 1 性能
                collector_stats = self.collector.get_performance_stats()

                # 获取 Phase 2 信号统计
                logger.info(
                    f"📊 Phase 2 Stats: "
                    f"{self.stats['total_signals']} signals "
                    f"(V4A:{self.stats['v4a_signals']}, "
                    f"V7:{self.stats['v7_signals']}, "
                    f"V8:{self.stats['v8_signals']}, "
                    f"LONG:{self.stats['long_signals']}) | "
                    f"Sent: {self.stats['signals_sent']}"
                )

                logger.info(
                    f"📊 Phase 1 Stats: "
                    f"{collector_stats['trades_per_second']} trades/s, "
                    f"{collector_stats['avg_latency_ms']}ms latency"
                )

        except asyncio.CancelledError:
            logger.info("Stats monitor task cancelled")


async def main():
    """主函数"""
    bot = CryptoMonitorBotPhase2()

    def signal_handler(signum, frame):
        logger.info("Received interrupt signal")
        asyncio.create_task(bot.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    await bot.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Phase 2 stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
