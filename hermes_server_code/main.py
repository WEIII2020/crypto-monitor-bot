#!/usr/bin/env python3
"""
Crypto Monitor Bot - MVP Version
Real-time cryptocurrency price monitoring with Telegram alerts
"""

import asyncio
import signal
import sys
from typing import Set

from src.utils.logger import logger
from src.utils.symbol_selector import SymbolSelector
from src.utils.performance_monitor import performance_monitor, periodic_stats_logger
from src.database.redis_client import redis_client
from src.database.postgres import postgres_client
from src.collectors.binance_collector import BinanceCollector
from src.analyzers.volatility_detector import VolatilityDetector
from src.analyzers.whale_detector_v2 import WhaleDetectorV2 as WhaleDetector
from src.analyzers.pump_dump_detector import PumpDumpDetector
from src.analyzers.oi_monitor import OIMonitor
from src.analyzers.square_monitor import SquareMonitor
from src.analyzers.signal_fusion import SignalFusion
from src.notifiers.telegram_notifier import TelegramNotifier


class CryptoMonitorBot:
    """Main application controller"""

    def __init__(self):
        self.running = False
        self.tasks: Set[asyncio.Task] = set()

        # Initialize components
        self.collector = BinanceCollector()
        self.detector = VolatilityDetector()
        self.whale_detector = WhaleDetector()
        self.pump_dump_detector = PumpDumpDetector()
        self.oi_monitor = OIMonitor()
        self.square_monitor = SquareMonitor()
        self.signal_fusion = SignalFusion()
        self.notifier = TelegramNotifier()
        self.symbol_selector = SymbolSelector()

        # Symbols will be loaded dynamically
        self.symbols = []

        # Signal buffer: 收集每个币种的信号
        self.signal_buffer: Dict[str, List[Dict]] = {}

    async def start(self):
        """Start the monitoring bot"""
        logger.info("🚀 Starting Crypto Monitor Bot...")

        try:
            # Connect to databases
            await redis_client.connect()
            await postgres_client.connect()
            logger.info("✅ Database connections established")

            # Select symbols dynamically
            logger.info("📊 Selecting optimal symbols for monitoring...")
            self.symbols = await self.symbol_selector.get_monitoring_list(max_symbols=50)
            logger.info(f"✅ Selected {len(self.symbols)} symbols")

            # Log first few symbols for verification
            preview = ', '.join(self.symbols[:10])
            logger.info(f"   Preview: {preview}...")

            # Connect to Binance
            success = await self.collector.connect_with_retry()
            if not success:
                logger.error("❌ Failed to connect to Binance")
                return

            # Subscribe to symbols
            await self.collector.subscribe_symbols(self.symbols)
            logger.info(f"✅ Subscribed to {len(self.symbols)} symbols")

            self.running = True

            # Start background tasks with intelligent scheduling
            collector_task = asyncio.create_task(self._run_collector())
            volatility_task = asyncio.create_task(self._run_volatility_check())
            whale_task = asyncio.create_task(self._run_whale_check())
            pump_dump_task = asyncio.create_task(self._run_pump_dump_check())
            oi_task = asyncio.create_task(self._run_oi_check())  # NEW: OI监控
            fusion_task = asyncio.create_task(self._run_signal_fusion())  # NEW: 信号融合
            stats_task = asyncio.create_task(periodic_stats_logger(interval=300))  # Every 5 minutes

            self.tasks.add(collector_task)
            self.tasks.add(volatility_task)
            self.tasks.add(whale_task)
            self.tasks.add(pump_dump_task)
            self.tasks.add(oi_task)
            self.tasks.add(fusion_task)
            self.tasks.add(stats_task)

            logger.info("✅ Bot is running! Press Ctrl+C to stop.")

            # Wait for tasks
            await asyncio.gather(*self.tasks)

        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")
            await self.stop()

    async def stop(self):
        """Stop the bot gracefully"""
        logger.info("🛑 Stopping Crypto Monitor Bot...")

        self.running = False

        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self.tasks, return_exceptions=True)

        # Disconnect from services
        await self.collector.disconnect()
        await redis_client.disconnect()
        await postgres_client.disconnect()

        logger.info("✅ Bot stopped successfully")

    async def _run_collector(self):
        """Run the price collector"""
        try:
            await self.collector.start_listening()
        except asyncio.CancelledError:
            logger.info("Collector task cancelled")
        except Exception as e:
            logger.error(f"Collector error: {e}")

    async def _run_volatility_check(self):
        """Run volatility detection (30s interval)"""
        try:
            while self.running:
                tasks = [
                    self.detector.check_volatility('binance', symbol)
                    for symbol in self.symbols
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, dict):
                        # 添加到信号缓冲区（用于融合）
                        symbol = result.get('symbol')
                        if symbol:
                            if symbol not in self.signal_buffer:
                                self.signal_buffer[symbol] = []
                            self.signal_buffer[symbol].append(result)

                        # 单独发送告警（原有逻辑）
                        await self.notifier.send_alert(result)

                await asyncio.sleep(30)  # 30秒检查一次

        except asyncio.CancelledError:
            logger.info("Volatility task cancelled")
        except Exception as e:
            logger.error(f"Volatility check error: {e}")

    async def _run_whale_check(self):
        """Run whale detection (60s interval)"""
        try:
            while self.running:
                tasks = [
                    self.whale_detector.check_whale_activity('binance', symbol)
                    for symbol in self.symbols
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, dict):
                        await self.notifier.send_alert(result)

                await asyncio.sleep(60)  # 60秒检查一次

        except asyncio.CancelledError:
            logger.info("Whale task cancelled")
        except Exception as e:
            logger.error(f"Whale check error: {e}")

    async def _run_pump_dump_check(self):
        """
        Run pump-dump detection with intelligent frequency

        - Normal symbols: 60s interval
        - Active pumps: 10s interval (monitoring for dump signal)
        - Open shorts: 5s interval (monitoring for exit)
        """
        try:
            while self.running:
                # 1. 检测所有币种的暴涨（60秒）
                tasks = [
                    self.pump_dump_detector.check_opportunity('binance', symbol)
                    for symbol in self.symbols
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, dict):
                        await self.notifier.send_alert(result)

                # 2. 高频监控：暴涨币种（等待弃盘点）
                active_pumps = self.pump_dump_detector.get_active_pumps()
                if active_pumps:
                    for _ in range(5):  # 10秒 × 5次 = 50秒内持续监控
                        if not self.running:
                            break

                        await asyncio.sleep(10)

                        high_freq_tasks = [
                            self.pump_dump_detector.check_opportunity('binance', symbol)
                            for symbol in active_pumps
                        ]

                        high_freq_results = await asyncio.gather(*high_freq_tasks, return_exceptions=True)

                        for result in high_freq_results:
                            if isinstance(result, dict):
                                await self.notifier.send_alert(result)

                        # 3. 超高频监控：已开仓币种（等待平仓）
                        active_shorts = self.pump_dump_detector.get_active_shorts()
                        if active_shorts:
                            ultra_high_tasks = [
                                self.pump_dump_detector.check_opportunity('binance', symbol)
                                for symbol in active_shorts
                            ]

                            ultra_results = await asyncio.gather(*ultra_high_tasks, return_exceptions=True)

                            for result in ultra_results:
                                if isinstance(result, dict):
                                    await self.notifier.send_alert(result)

                await asyncio.sleep(10)  # 主循环60秒

        except asyncio.CancelledError:
            logger.info("Pump-dump task cancelled")
        except Exception as e:
            logger.error(f"Pump-dump check error: {e}")

    async def _run_oi_check(self):
        """
        Run OI (Open Interest) monitoring (lana's method)

        - Check every 120s (2 minutes)
        - Detect 48h OI spike with no price move
        """
        try:
            while self.running:
                tasks = [
                    self.oi_monitor.check_oi_spike('binance', symbol)
                    for symbol in self.symbols
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, dict):
                        # 添加到信号缓冲区
                        symbol = result.get('symbol')
                        if symbol:
                            if symbol not in self.signal_buffer:
                                self.signal_buffer[symbol] = []
                            self.signal_buffer[symbol].append(result)

                        # 单独发送告警
                        await self.notifier.send_alert(result)

                await asyncio.sleep(120)  # 2分钟检查一次

        except asyncio.CancelledError:
            logger.info("OI monitoring task cancelled")
        except Exception as e:
            logger.error(f"OI monitoring error: {e}")

    async def _run_signal_fusion(self):
        """
        Run signal fusion (lana's multi-dimensional analysis)

        - Check every 60s
        - Fuse signals from all detectors
        - Send high-score alerts (≥60 points)
        """
        try:
            while self.running:
                await asyncio.sleep(60)  # 等待60秒让信号积累

                # 遍历所有有信号的币种
                for symbol in list(self.signal_buffer.keys()):
                    signals = self.signal_buffer.get(symbol, [])

                    if not signals:
                        continue

                    # 执行信号融合
                    fused_signal = await self.signal_fusion.fuse_signals(symbol, signals)

                    if fused_signal:
                        # 发送融合后的告警
                        await self.notifier.send_alert(fused_signal)

                    # 清空该币种的信号缓冲区（避免重复）
                    self.signal_buffer[symbol] = []

        except asyncio.CancelledError:
            logger.info("Signal fusion task cancelled")
        except Exception as e:
            logger.error(f"Signal fusion error: {e}")


async def main():
    """Main entry point"""
    bot = CryptoMonitorBot()

    # Setup signal handlers
    def signal_handler(sig, frame):
        logger.info("Received interrupt signal")
        asyncio.create_task(bot.stop())

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start the bot
    await bot.start()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
