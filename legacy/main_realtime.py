#!/usr/bin/env python3
"""
Crypto Monitor Bot - Realtime Version (Phase 1)
毫秒级实时监控系统
"""

import asyncio
import signal
import sys
from typing import Set
from datetime import datetime

from src.utils.logger import logger
from src.utils.symbol_selector import SymbolSelector
from src.utils.performance_monitor import performance_monitor, periodic_stats_logger
from src.database.redis_client import redis_client
from src.database.postgres import postgres_client
from src.collectors.binance_realtime_collector import BinanceRealtimeCollector
from src.analyzers.volatility_detector import VolatilityDetector
from src.analyzers.whale_detector_v2 import WhaleDetectorV2 as WhaleDetector
from src.notifiers.telegram_notifier import TelegramNotifier


class CryptoMonitorBotRealtime:
    """实时监控 Bot (毫秒级)"""

    def __init__(self):
        self.running = False
        self.tasks: Set[asyncio.Task] = set()

        # 使用新的实时采集器
        self.collector = BinanceRealtimeCollector()
        self.detector = VolatilityDetector()
        self.whale_detector = WhaleDetector()
        self.notifier = TelegramNotifier()
        self.symbol_selector = SymbolSelector()

        self.symbols = []

        # 性能监控间隔（秒）
        self.stats_interval = 30  # 每30秒报告一次性能

    async def start(self):
        """启动实时监控"""
        logger.info("🚀 Starting Realtime Crypto Monitor Bot...")

        try:
            # 连接数据库
            await redis_client.connect()
            await postgres_client.connect()
            logger.info("✅ Database connections established")

            # 选择币种（可以先测试少量币种）
            test_mode = False  # 设为 True 进行小规模测试

            if test_mode:
                # 测试模式：只监控5个主流币
                self.symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
                logger.info(f"🧪 Test mode: monitoring {len(self.symbols)} symbols")
            else:
                # 生产模式：200个币种
                logger.info("📊 Selecting optimal symbols for monitoring...")
                self.symbols = await self.symbol_selector.get_monitoring_list(max_symbols=200)
                logger.info(f"✅ Selected {len(self.symbols)} symbols")

            # 连接到 Binance
            success = await self.collector.connect_with_retry()
            if not success:
                logger.error("❌ Failed to connect to Binance")
                return

            # 订阅实时成交流
            await self.collector.subscribe_symbols(self.symbols)
            logger.info(f"✅ Subscribed to {len(self.symbols)} realtime streams")

            self.running = True

            # 启动后台任务
            collector_task = asyncio.create_task(self._run_collector())
            analysis_task = asyncio.create_task(self._run_realtime_analysis())
            stats_task = asyncio.create_task(self._run_performance_monitor())

            self.tasks.add(collector_task)
            self.tasks.add(analysis_task)
            self.tasks.add(stats_task)

            logger.info("✅ Realtime Bot is running! Press Ctrl+C to stop.")

            # 等待所有任务
            await asyncio.gather(*self.tasks, return_exceptions=True)

        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")
            await self.stop()

    async def stop(self):
        """停止监控"""
        logger.info("🛑 Stopping Realtime Monitor Bot...")
        self.running = False

        # 取消所有任务
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # 断开连接
        await self.collector.disconnect()
        await redis_client.disconnect()
        await postgres_client.disconnect()

        logger.info("✅ Bot stopped successfully")

    async def _run_collector(self):
        """运行采集器"""
        try:
            await self.collector.listen()
        except asyncio.CancelledError:
            logger.info("Collector task cancelled")
        except Exception as e:
            logger.error(f"Collector error: {e}")

    async def _run_realtime_analysis(self):
        """实时分析（毫秒级触发）"""
        logger.info("🔍 Starting realtime analysis...")

        last_check = {}  # 记录每个币种上次检查时间
        check_interval_ms = 1000  # 每1秒检查一次（可调整）

        try:
            while self.running:
                now_ms = int(datetime.now().timestamp() * 1000)

                for symbol in self.symbols:
                    try:
                        # 限流：避免过于频繁
                        if symbol in last_check:
                            if now_ms - last_check[symbol] < check_interval_ms:
                                continue

                        last_check[symbol] = now_ms

                        # 获取实时指标（从滑动窗口）
                        metrics_1m = await self.collector.get_realtime_metrics(symbol, '1m')

                        if not metrics_1m:
                            continue

                        # 检测异常（快速检查）
                        await self._check_realtime_signals(symbol, metrics_1m)

                    except Exception as e:
                        logger.error(f"Error analyzing {symbol}: {e}")

                # 短暂休眠，避免CPU占用过高
                await asyncio.sleep(0.1)  # 100ms

        except asyncio.CancelledError:
            logger.info("Realtime analysis task cancelled")
        except Exception as e:
            logger.error(f"Realtime analysis error: {e}")

    async def _check_realtime_signals(self, symbol: str, metrics: dict):
        """
        检查实时信号

        Args:
            symbol: 币种
            metrics: 实时指标
        """
        # 1. 价格剧烈波动
        price_change = metrics['price_change_pct']
        if abs(price_change) > 2.0:  # 1分钟涨跌超过2%
            logger.warning(
                f"⚡ {symbol} 1m price spike: {price_change:+.2f}% "
                f"(Buy: {metrics['buy_ratio']:.1f}%, Sell: {metrics['sell_ratio']:.1f}%)"
            )

            # 可选：发送 Telegram 通知
            # await self.notifier.send_alert(...)

        # 2. 买卖压力失衡
        buy_ratio = metrics['buy_ratio']
        if buy_ratio > 70:  # 买方主导
            logger.info(f"🟢 {symbol} Strong buying pressure: {buy_ratio:.1f}%")
        elif buy_ratio < 30:  # 卖方主导
            logger.info(f"🔴 {symbol} Strong selling pressure: {buy_ratio:.1f}%")

        # 3. 成交量异常
        volume_ratio = metrics.get('volume_ratio', 1.0)
        if volume_ratio > 3.0:  # 成交量3倍
            logger.warning(f"📊 {symbol} Volume spike: {volume_ratio:.1f}x")

        # 4. 大单检测
        large_orders = await self.collector.get_large_orders(symbol, min_usdt=50000)
        if large_orders:
            for order in large_orders[:3]:  # 只显示前3个
                logger.info(
                    f"🐋 {symbol} Large order: {order['side']} "
                    f"${order['quote_qty']:,.0f} @ ${order['price']:,.2f}"
                )

    async def _run_performance_monitor(self):
        """性能监控"""
        logger.info("📈 Starting performance monitor...")

        try:
            while self.running:
                await asyncio.sleep(self.stats_interval)

                # 获取采集器性能
                stats = self.collector.get_performance_stats()

                logger.info(
                    f"📊 Performance: "
                    f"{stats['total_trades']} trades, "
                    f"{stats['trades_per_second']} trades/s, "
                    f"{stats['avg_latency_ms']}ms latency, "
                    f"{stats['active_symbols']} symbols"
                )

        except asyncio.CancelledError:
            logger.info("Performance monitor task cancelled")


async def main():
    """主函数"""
    bot = CryptoMonitorBotRealtime()

    # 信号处理
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
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
