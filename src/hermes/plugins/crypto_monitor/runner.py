"""
Runs the crypto-monitor-bot's analysis loop as an asyncio background task
inside the Hermes process.

Requires CRYPTO_MONITOR_BOT_PATH env var pointing to the crypto-monitor-bot
directory (default: /opt/crypto-monitor-bot).

When that path exists, this module imports the monitoring components, patches
the TelegramNotifier to use Hermes's Bot instance, and runs the full monitoring
loop (data collection → analysis → alert delivery).

If the path is absent, the runner silently disables itself — Hermes still works
and the query commands still function (they read from the shared DB).
"""

import asyncio
import logging
import os
import sys
from typing import Optional, Set

logger = logging.getLogger(__name__)


class CryptoMonitorRunner:
    """Background runner that starts the crypto monitoring loop inside Hermes."""

    def __init__(self, bot, chat_id: str):
        """
        Args:
            bot: python-telegram-bot Bot instance (from Hermes's Application)
            chat_id: Telegram chat ID to send alerts to
        """
        self.bot = bot
        self.chat_id = str(chat_id)
        self.running = False
        self._tasks: Set[asyncio.Task] = set()
        self._crypto_path: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self):
        """Start the monitoring background tasks. No-op if path not configured."""
        path = os.getenv("CRYPTO_MONITOR_BOT_PATH", "/opt/crypto-monitor-bot")
        if not os.path.isdir(path):
            logger.info(
                "CryptoMonitorRunner: CRYPTO_MONITOR_BOT_PATH=%s not found — "
                "monitoring loop disabled (query commands still work)",
                path,
            )
            return

        self._crypto_path = path
        if path not in sys.path:
            sys.path.insert(0, path)

        # Set env vars that crypto-monitor-bot's config.py expects
        os.environ.setdefault("TELEGRAM_CHAT_ID", self.chat_id)
        # TELEGRAM_BOT_TOKEN is already set (Hermes's token)

        try:
            await self._start_monitoring()
        except Exception as e:
            logger.error("CryptoMonitorRunner failed to start: %s", e, exc_info=True)

    async def stop(self):
        self.running = False
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _start_monitoring(self):
        try:
            from src.database.redis_client import redis_client
            from src.database.postgres import postgres_client
            from src.collectors.binance_collector import BinanceCollector
            from src.analyzers.volatility_detector import VolatilityDetector
            from src.analyzers.whale_detector_v2 import WhaleDetectorV2
            from src.analyzers.pump_dump_detector import PumpDumpDetector
            from src.analyzers.oi_monitor import OIMonitor
            from src.analyzers.signal_fusion import SignalFusion
            from src.utils.symbol_selector import SymbolSelector
        except ImportError as exc:
            logger.error(
                "CryptoMonitorRunner: failed to import crypto-monitor-bot modules "
                "from %s: %s",
                self._crypto_path,
                exc,
            )
            return

        logger.info("CryptoMonitorRunner: connecting to databases...")
        try:
            await redis_client.connect()
            await postgres_client.connect()
        except Exception as exc:
            logger.error("CryptoMonitorRunner: DB connect failed: %s", exc)
            return

        # Build a notifier that routes alerts through Hermes's Bot
        notifier = _HermesNotifier(self.bot, self.chat_id, postgres_client)

        selector = SymbolSelector()
        symbols = await selector.get_monitoring_list(max_symbols=200)
        logger.info("CryptoMonitorRunner: monitoring %d symbols", len(symbols))

        collector = BinanceCollector()
        success = await collector.connect_with_retry()
        if not success:
            logger.error("CryptoMonitorRunner: Binance WebSocket connect failed")
            return
        await collector.subscribe_symbols(symbols)

        detector = VolatilityDetector()
        whale = WhaleDetectorV2()
        pump = PumpDumpDetector()
        oi = OIMonitor()
        fusion = SignalFusion()

        self.running = True
        loop = asyncio.get_running_loop()

        def _make_task(coro):
            t = loop.create_task(coro)
            self._tasks.add(t)
            t.add_done_callback(self._tasks.discard)
            return t

        _make_task(_run_loop("collector", collector.run(), self))
        _make_task(_check_loop("volatility", detector, collector, notifier, symbols, 30, self))
        _make_task(_check_loop("whale", whale, collector, notifier, symbols, 60, self))
        _make_task(_check_loop("pump_dump", pump, collector, notifier, symbols, 60, self))
        _make_task(_check_loop("oi", oi, collector, notifier, symbols, 120, self))
        _make_task(_fusion_loop(fusion, notifier, symbols, 60, self))

        logger.info("CryptoMonitorRunner: all monitoring tasks started")


# ---------------------------------------------------------------------------
# Lightweight loop helpers
# ---------------------------------------------------------------------------

async def _run_loop(name: str, coro, runner: CryptoMonitorRunner):
    """Wrap a long-running coroutine; restart on unexpected exit."""
    while runner.running:
        try:
            await coro
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("CryptoMonitorRunner [%s] crashed: %s — restarting in 10s", name, exc)
            await asyncio.sleep(10)


async def _check_loop(name, analyzer, collector, notifier, symbols, interval, runner):
    """Periodically call analyzer.check_* for every symbol."""
    method_names = [
        f"check_{name.split('_')[0]}",  # check_volatility, check_whale, etc.
        "check_opportunity",            # pump_dump_detector
        "check_oi_spike",               # oi_monitor
        "check_whale_activity",
    ]
    check_fn = None
    for m in method_names:
        if hasattr(analyzer, m):
            check_fn = getattr(analyzer, m)
            break
    if check_fn is None:
        logger.warning("CryptoMonitorRunner: no check method found on %s", analyzer)
        return

    while runner.running:
        try:
            for symbol in symbols:
                try:
                    data = collector.get_symbol_data(symbol)
                    if not data:
                        continue
                    result = await check_fn(symbol, data)
                    if result and result.get("alert"):
                        await notifier.send_alert(result)
                except Exception as exc:
                    logger.debug("CryptoMonitorRunner [%s] symbol %s: %s", name, symbol, exc)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("CryptoMonitorRunner [%s] loop error: %s", name, exc)
        await asyncio.sleep(interval)


async def _fusion_loop(fusion, notifier, symbols, interval, runner):
    """Run signal fusion across all symbols."""
    while runner.running:
        try:
            for symbol in symbols:
                try:
                    result = await fusion.fuse_signals(symbol)
                    if result and result.get("alert"):
                        await notifier.send_alert(result)
                except Exception:
                    pass
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.warning("CryptoMonitorRunner [fusion] loop error: %s", exc)
        await asyncio.sleep(interval)


# ---------------------------------------------------------------------------
# Notifier that uses Hermes's Bot instance
# ---------------------------------------------------------------------------

class _HermesNotifier:
    """Sends crypto alerts through Hermes's Bot (same token, same chat)."""

    def __init__(self, bot, chat_id: str, postgres_client=None):
        self.bot = bot
        self.chat_id = chat_id
        self._pg = postgres_client

    async def send_alert(self, alert_data: dict):
        try:
            message = self._format(alert_data)
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode="HTML",
            )
            # Persist to DB if available
            if self._pg:
                try:
                    symbol_record = await self._pg.get_symbol(
                        alert_data.get("symbol", ""),
                        alert_data.get("exchange", "binance"),
                    )
                    if symbol_record:
                        await self._pg.insert_alert({
                            "symbol_id": symbol_record["id"],
                            "exchange": alert_data.get("exchange", "binance"),
                            "alert_type": alert_data.get("alert_type", "UNKNOWN"),
                            "alert_level": alert_data.get("alert_level", "WARNING"),
                            "price": alert_data.get("price", 0),
                            "change_percent": alert_data.get("change_percent", 0),
                            "message": alert_data.get("message", ""),
                        })
                except Exception as db_exc:
                    logger.debug("_HermesNotifier DB persist failed: %s", db_exc)
        except Exception as exc:
            logger.error("_HermesNotifier.send_alert error: %s", exc)

    def _format(self, d: dict) -> str:
        level_em = "🚨" if d.get("alert_level") == "CRITICAL" else "⚠️"
        pct = d.get("change_percent", 0)
        dir_em = "📈" if pct > 0 else "📉"
        from datetime import datetime
        return (
            f"{level_em} <b>{d.get('alert_level','WARNING')} ALERT</b>\n\n"
            f"{dir_em} <b>{d.get('symbol','?')}</b> — {d.get('alert_type','')}\n\n"
            f"💰 价格: ${d.get('price', 0):.4f}\n"
            f"📊 变化: <b>{pct:+.2f}%</b>\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}"
        )
