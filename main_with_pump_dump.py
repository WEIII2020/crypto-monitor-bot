#!/usr/bin/env python3
"""
Crypto Monitor Bot - 集成妖币策略版本

⚠️ 警告：这个版本包含主动交易策略
⚠️ 请先阅读 PUMP_DUMP_QUICK_START.md
⚠️ 建议先使用纸面交易测试1-2周

使用方法：
1. 确保 config.yaml 中 pump_dump_strategy.enabled = true
2. python main_with_pump_dump.py
"""

import asyncio
import signal
import sys
import yaml
from typing import Set
from pathlib import Path

from src.utils.logger import logger
from src.utils.symbol_selector import SymbolSelector
from src.utils.performance_monitor import performance_monitor, periodic_stats_logger
from src.database.redis_client import redis_client
from src.database.postgres import postgres_client
from src.collectors.binance_collector import BinanceCollector
from src.analyzers.volatility_detector import VolatilityDetector
from src.analyzers.whale_detector_v2 import WhaleDetectorV2 as WhaleDetector
from src.analyzers.market_maker_detector import MarketMakerDetector
from src.analyzers.manipulation_coin_detector import ManipulationCoinDetector
from src.analyzers.pump_dump_detector import PumpDumpDetector
from src.notifiers.telegram_notifier import TelegramNotifier


class CryptoMonitorBot:
    """Main application controller with Pump & Dump strategy"""

    def __init__(self):
        self.running = False
        self.tasks: Set[asyncio.Task] = set()

        # Load configuration
        self.config = self._load_config()

        # Check if pump-dump strategy is enabled
        self.pump_dump_enabled = self.config.get('pump_dump_strategy', {}).get('enabled', False)

        # Initialize components
        self.collector = BinanceCollector()
        self.detector = VolatilityDetector()
        self.whale_detector = WhaleDetector()
        self.market_maker_detector = MarketMakerDetector()
        self.notifier = TelegramNotifier()
        self.symbol_selector = SymbolSelector()

        # Pump & Dump components (conditional)
        if self.pump_dump_enabled:
            logger.warning("⚠️  妖币策略已启用 - 这是主动交易策略！")
            self.manipulation_detector = ManipulationCoinDetector()
            self.pump_dump_detector = PumpDumpDetector()
        else:
            logger.info("ℹ️  妖币策略未启用（被动监控模式）")
            self.manipulation_detector = None
            self.pump_dump_detector = None

        # Symbols will be loaded dynamically
        self.symbols = []
        self.manipulation_coins = []

    def _load_config(self):
        """Load configuration from config.yaml"""
        config_path = Path(__file__).parent / 'config.yaml'
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}

    async def start(self):
        """Start the monitoring bot"""
        logger.info("🚀 Starting Crypto Monitor Bot...")

        if self.pump_dump_enabled:
            logger.warning("=" * 60)
            logger.warning("⚠️  妖币策略已启用")
            logger.warning("⚠️  这是主动交易策略，不是被动监控")
            logger.warning("⚠️  请确保你已阅读 PUMP_DUMP_QUICK_START.md")
            logger.warning("⚠️  建议先纸面交易1-2周")
            logger.warning("=" * 60)

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

            # Start background tasks
            collector_task = asyncio.create_task(self._run_collector())
            analyzer_task = asyncio.create_task(self._run_analyzer())
            stats_task = asyncio.create_task(periodic_stats_logger(interval=300))

            self.tasks.add(collector_task)
            self.tasks.add(analyzer_task)
            self.tasks.add(stats_task)

            # Start pump-dump specific tasks
            if self.pump_dump_enabled:
                pump_dump_task = asyncio.create_task(self._run_pump_dump_monitor())
                self.tasks.add(pump_dump_task)

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

    async def _run_analyzer(self):
        """Run the price analyzer"""
        try:
            while self.running:
                # Check each symbol for volatility and whale activity
                for symbol in self.symbols:
                    # Check basic volatility
                    volatility_alert = await self.detector.check_volatility('binance', symbol)
                    if volatility_alert:
                        await self.notifier.send_alert(volatility_alert)

                    # Check whale/market maker behavior (V2: Multi-timeframe analysis)
                    whale_alert = await self.whale_detector.check_whale_activity('binance', symbol)
                    if whale_alert:
                        await self.notifier.send_alert(whale_alert)

                    # Check market manipulation (Comprehensive manipulation detection)
                    mm_alert = await self.market_maker_detector.check_manipulation('binance', symbol)
                    if mm_alert:
                        await self.notifier.send_alert(mm_alert)

                # Check every 30 seconds
                await asyncio.sleep(30)

        except asyncio.CancelledError:
            logger.info("Analyzer task cancelled")
        except Exception as e:
            logger.error(f"Analyzer error: {e}")

    async def _run_pump_dump_monitor(self):
        """Run pump & dump strategy monitor (仅当启用时)"""
        if not self.pump_dump_enabled:
            return

        try:
            logger.info("🚀 Pump & Dump monitor started")

            while self.running:
                # 每小时更新妖币池
                if self.manipulation_detector.should_update():
                    logger.info("🔄 Updating manipulation coin pool...")
                    self.manipulation_coins = await self.manipulation_detector.update_coin_pool(
                        self.symbols
                    )

                # 检查所有币种的pump & dump机会
                for symbol in self.symbols:
                    # 判断是否为妖币
                    is_manipulation = self.manipulation_detector.is_manipulation_coin(symbol)

                    # 检测pump & dump机会
                    pump_dump_alert = await self.pump_dump_detector.check_opportunity(
                        'binance',
                        symbol,
                        is_manipulation
                    )

                    if pump_dump_alert:
                        # 发送告警
                        await self.notifier.send_alert(pump_dump_alert)

                        # 根据告警类型添加特殊标记
                        alert_type = pump_dump_alert.get('alert_type')
                        if alert_type == 'EARLY_SHORT_SIGNAL':
                            logger.warning("🚨 早空信号触发！请检查Telegram")
                        elif alert_type == 'TAKE_PROFIT':
                            logger.info("✅ 止盈信号触发")
                        elif alert_type == 'STOP_LOSS':
                            logger.warning("🔴 止损信号触发")

                # 清理过期头寸
                self.pump_dump_detector.clear_expired_positions()

                # 每30秒检查一次
                await asyncio.sleep(30)

        except asyncio.CancelledError:
            logger.info("Pump & Dump monitor task cancelled")
        except Exception as e:
            logger.error(f"Pump & Dump monitor error: {e}")


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
