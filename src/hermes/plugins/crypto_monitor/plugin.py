"""
CryptoMonitorPlugin — wires the monitor commands and background runner
into Hermes's Telegram Application.

Usage (in telegram.py):
    from tools.crypto_monitor import CryptoMonitorPlugin
    plugin = CryptoMonitorPlugin()
    plugin.register_handlers(self._app)        # before app.start()
    await plugin.start(self._bot, chat_id)     # after app.start()
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from telegram.ext import CommandHandler, CallbackQueryHandler
    _TELEGRAM_AVAILABLE = True
except ImportError:
    _TELEGRAM_AVAILABLE = False

from .data_reader import MonitorDataReader
from .commands import CryptoMonitorCommands
from .runner import CryptoMonitorRunner


class CryptoMonitorPlugin:
    """Integrates crypto-monitor-bot alert/query functionality into Hermes."""

    def __init__(self):
        self._reader = MonitorDataReader()
        self._commands: Optional[CryptoMonitorCommands] = None
        self._runner: Optional[CryptoMonitorRunner] = None

    def register_handlers(self, app) -> None:
        """Register /monitor_* CommandHandlers on the Telegram Application.

        Must be called BEFORE the catch-all COMMAND MessageHandler is added,
        so these specific commands take priority.
        """
        if not _TELEGRAM_AVAILABLE:
            return

        self._commands = CryptoMonitorCommands(self._reader)
        cmds = self._commands

        app.add_handler(CommandHandler("monitor_status", cmds.cmd_monitor_status))
        app.add_handler(CommandHandler("monitor_stats", cmds.cmd_monitor_stats))
        app.add_handler(CommandHandler("recent_alerts", cmds.cmd_recent_alerts))
        app.add_handler(CommandHandler("fusion_signals", cmds.cmd_fusion_signals))
        app.add_handler(CommandHandler("auto_trade", cmds.cmd_auto_trade))
        app.add_handler(CommandHandler("help_monitor", cmds.cmd_help_monitor))
        # Crypto-specific inline-button callbacks (prefixed "cm_" to avoid conflicts)
        app.add_handler(CallbackQueryHandler(cmds.handle_callback, pattern=r"^cm_"))

        logger.info("CryptoMonitorPlugin: registered 6 commands + callback handler")

    async def start(self, bot, chat_id: str) -> None:
        """Connect to DB and start background monitoring loop."""
        connected = await self._reader.connect()
        if connected:
            logger.info("CryptoMonitorPlugin: DB reader connected")
        else:
            logger.warning(
                "CryptoMonitorPlugin: DB reader could not connect — "
                "query commands will return empty results"
            )

        # Start the monitoring runner (no-op if CRYPTO_MONITOR_BOT_PATH not set)
        self._runner = CryptoMonitorRunner(bot, chat_id)
        await self._runner.start()

    async def stop(self) -> None:
        if self._runner:
            await self._runner.stop()
        if self._reader:
            await self._reader.disconnect()
