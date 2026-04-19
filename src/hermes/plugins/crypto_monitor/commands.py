"""
Telegram command handlers for crypto monitoring queries.
These are registered into Hermes's existing Telegram bot (no separate bot needed).
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import ContextTypes
except ImportError:
    Update = object
    InlineKeyboardButton = object
    InlineKeyboardMarkup = object

    class _MockContextTypes:
        DEFAULT_TYPE = object

    ContextTypes = _MockContextTypes


_TYPE_EMOJI = {
    "PRICE_SPIKE": "📈",
    "OI_SPIKE": "🔥",
    "WHALE_ACTIVITY": "🐋",
    "PUMP_DETECTED": "🚀",
    "SIGNAL_FUSION": "🎯",
    "SQUARE_TRENDING": "💬",
}


def _emoji(alert_type: str) -> str:
    return _TYPE_EMOJI.get(alert_type, "📊")


class CryptoMonitorCommands:
    """Handlers for /monitor_* commands, attached to Hermes's Telegram Application."""

    def __init__(self, reader):
        self.reader = reader  # MonitorDataReader instance

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    async def cmd_monitor_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔍 正在检查监控系统状态...")
        status = await self.reader.get_monitor_status()
        text = (
            "📊 <b>Crypto Monitor 状态</b>\n\n"
            f"🗄 PostgreSQL: {'✅ 已连接' if status['postgres_connected'] else '❌ 断开'}\n"
            f"⚡ Redis: {'✅ 已连接' if status['redis_connected'] else '❌ 断开'}\n"
            f"📈 监控币种: <b>{status['symbols_count']}</b> 个\n"
            f"🔔 最近1h告警: <b>{status['recent_alerts']}</b> 条\n"
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        await update.message.reply_text(text, parse_mode="HTML")

    async def cmd_monitor_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        hours = 24
        if context.args:
            try:
                hours = int(context.args[0])
            except ValueError:
                pass
        await update.message.reply_text(f"📊 统计过去 {hours}h 数据中...")
        stats = await self.reader.get_alert_stats(hours=hours)
        lines = [f"📈 <b>过去 {hours}h 统计</b>", f"🔔 总告警: <b>{stats['total']}</b> 条", "", "按类型:"]
        for t, cnt in stats["by_type"].items():
            pct = cnt / stats["total"] * 100 if stats["total"] else 0
            lines.append(f"  {_emoji(t)} {t}: {cnt} ({pct:.1f}%)")
        lines.append("\n按级别:")
        for lv, cnt in stats["by_level"].items():
            pct = cnt / stats["total"] * 100 if stats["total"] else 0
            em = "🚨" if lv == "CRITICAL" else "⚠️" if lv == "WARNING" else "ℹ️"
            lines.append(f"  {em} {lv}: {cnt} ({pct:.1f}%)")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def cmd_recent_alerts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        minutes = 60
        if context.args:
            try:
                minutes = int(context.args[0])
            except ValueError:
                pass
        alerts = await self.reader.get_recent_alerts(minutes=minutes)
        if not alerts:
            await update.message.reply_text(f"✅ 最近 {minutes}min 没有告警")
            return
        lines = [f"📢 <b>最近 {minutes}min 告警</b>（共 {len(alerts)} 条）\n"]
        for i, a in enumerate(alerts[:10], 1):
            lines.append(
                f"{i}. {_emoji(a.alert_type)} <b>{a.symbol}</b>  {a.alert_type}\n"
                f"   ${a.price:.4f}  {a.change_percent:+.2f}%  "
                f"{a.created_at.strftime('%H:%M:%S')}"
            )
        if len(alerts) > 10:
            lines.append(f"\n…还有 {len(alerts) - 10} 条")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    async def cmd_fusion_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        min_score = 85
        if context.args:
            try:
                min_score = int(context.args[0])
            except ValueError:
                pass
        signals = await self.reader.get_fusion_signals(minutes=30, min_score=min_score)
        if not signals:
            await update.message.reply_text(
                f"暂无 ≥{min_score} 分的融合信号\n💡 /fusion_signals 60 可降低阈值"
            )
            return
        lines = [f"🟢 <b>融合信号 ≥{min_score}分</b>\n"]
        for s in signals:
            direction = "🎯 买入" if "BUY" in s.message else "👀 观察"
            lines.append(
                f"🪙 <b>{s.symbol}</b>  {s.score}/100\n"
                f"   ${s.price:.4f}  {direction}  "
                f"{s.created_at.strftime('%H:%M:%S')}"
            )
        keyboard = [[
            InlineKeyboardButton("🤖 自动交易", callback_data=f"cm_trade_{min_score}"),
            InlineKeyboardButton("📊 刷新", callback_data=f"cm_refresh_{min_score}"),
        ]]
        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def cmd_auto_trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        signals = await self.reader.get_fusion_signals(minutes=10, min_score=85)
        if not signals:
            await update.message.reply_text(
                "暂无可交易信号\n要求: 评分 ≥85 · 时间 ≤10min · 含 OI_SPIKE"
            )
            return
        lines = [f"🎯 <b>发现 {len(signals)} 个可交易信号</b>\n"]
        for i, s in enumerate(signals, 1):
            lines.append(f"{i}. <b>{s.symbol}</b> — {s.score}分")
        lines += [
            "\n⚠️ <b>Lana 规则:</b>",
            "• 止损: 亏 200 USDT 立即平仓",
            "• 持仓: ≤1 小时",
            "\n确认执行自动交易？",
        ]
        keyboard = [[
            InlineKeyboardButton("✅ 确认", callback_data="cm_exec_trade"),
            InlineKeyboardButton("❌ 取消", callback_data="cm_cancel"),
        ]]
        await update.message.reply_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    async def cmd_help_monitor(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = (
            "🤖 <b>Crypto Monitor 命令</b>\n\n"
            "<b>查询:</b>\n"
            "  /monitor_status — 系统状态\n"
            "  /monitor_stats [h] — 统计 (默认24h)\n"
            "  /recent_alerts [min] — 最近告警 (默认60min)\n"
            "  /fusion_signals [score] — 融合信号 (默认≥85)\n\n"
            "<b>交易:</b>\n"
            "  /auto_trade — 检查可交易信号\n\n"
            "<b>示例:</b>\n"
            "  /monitor_stats 48  →  48h 统计\n"
            "  /fusion_signals 75  →  ≥75分信号"
        )
        await update.message.reply_text(text, parse_mode="HTML")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data or ""

        if data.startswith("cm_refresh_"):
            min_score = int(data.split("_")[2])
            signals = await self.reader.get_fusion_signals(minutes=30, min_score=min_score)
            if signals:
                lines = [f"🔄 <b>刷新 — 融合信号 ≥{min_score}分</b>\n"]
                for s in signals:
                    direction = "🎯 买入" if "BUY" in s.message else "👀 观察"
                    lines.append(f"🪙 <b>{s.symbol}</b>  {s.score}/100  {direction}")
                await query.edit_message_text("\n".join(lines), parse_mode="HTML")
            else:
                await query.edit_message_text(f"暂无 ≥{min_score} 分信号")

        elif data.startswith("cm_trade_"):
            await query.edit_message_text("请使用 /auto_trade 命令确认执行")

        elif data == "cm_exec_trade":
            await query.edit_message_text(
                "⚠️ 此功能需要配置 Binance API Key\n"
                "请在 .env 中设置 BINANCE_API_KEY / BINANCE_API_SECRET"
            )

        elif data == "cm_cancel":
            await query.edit_message_text("❌ 已取消")
