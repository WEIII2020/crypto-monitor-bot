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
from src.database.redis_client import redis_client
from src.database.postgres import postgres_client
from src.collectors.binance_collector import BinanceCollector
from src.analyzers.volatility_detector import VolatilityDetector
from src.notifiers.telegram_notifier import TelegramNotifier


class CryptoMonitorBot:
    """Main application controller"""

    def __init__(self):
        self.running = False
        self.tasks: Set[asyncio.Task] = set()

        # Initialize components
        self.collector = BinanceCollector()
        self.detector = VolatilityDetector()
        self.notifier = TelegramNotifier()

        # Symbols to monitor (configurable)
        self.symbols = [
            'BTC/USDT',
            'ETH/USDT',
            'BNB/USDT',
            'SOL/USDT',
            'XRP/USDT'
        ]

    async def start(self):
        """Start the monitoring bot"""
        logger.info("🚀 Starting Crypto Monitor Bot...")

        try:
            # Connect to databases
            await redis_client.connect()
            await postgres_client.connect()
            logger.info("✅ Database connections established")

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

            self.tasks.add(collector_task)
            self.tasks.add(analyzer_task)

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
                # Check each symbol for volatility
                for symbol in self.symbols:
                    alert = await self.detector.check_volatility('binance', symbol)

                    if alert:
                        # Send notification
                        await self.notifier.send_alert(alert)

                # Check every 30 seconds
                await asyncio.sleep(30)

        except asyncio.CancelledError:
            logger.info("Analyzer task cancelled")
        except Exception as e:
            logger.error(f"Analyzer error: {e}")


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
