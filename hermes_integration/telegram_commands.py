"""
Hermes Agent - Telegram Commands
Telegram Bot 命令处理器
"""

import asyncio
from datetime import datetime
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

from monitor_data_reader import MonitorDataReader


class HermesMonitorCommands:
    """Hermes Agent的Monitor相关命令"""

    def __init__(self, telegram_token: str):
        self.token = telegram_token
        self.reader = MonitorDataReader()
        self.app = None

    async def start_bot(self):
        """启动Telegram Bot"""
        # 创建应用
        self.app = Application.builder().token(self.token).build()

        # 连接数据库
        await self.reader.connect()

        # 注册命令
        self.app.add_handler(CommandHandler("monitor_status", self.cmd_monitor_status))
        self.app.add_handler(CommandHandler("monitor_stats", self.cmd_monitor_stats))
        self.app.add_handler(CommandHandler("recent_alerts", self.cmd_recent_alerts))
        self.app.add_handler(CommandHandler("fusion_signals", self.cmd_fusion_signals))
        self.app.add_handler(CommandHandler("optimize", self.cmd_optimize))
        self.app.add_handler(CommandHandler("auto_trade", self.cmd_auto_trade))
        self.app.add_handler(CommandHandler("help_monitor", self.cmd_help))

        # 回调查询处理
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

        # 启动
        print("🤖 Hermes Monitor Commands 已启动")
        await self.app.run_polling()

    async def cmd_monitor_status(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """查看监控系统状态"""
        await update.message.reply_text("🔍 正在检查监控系统状态...")

        status = await self.reader.get_monitor_status()

        message = f"""
📊 **Crypto Monitor Bot 状态**

🔗 数据库连接:
  • PostgreSQL: {'✅ 已连接' if status['postgres_connected'] else '❌ 断开'}
  • Redis: {'✅ 已连接' if status['redis_connected'] else '❌ 断开'}

📈 监控范围:
  • 币种数量: **{status['symbols_count']}个**
  • 最近1h告警: **{status['recent_alerts']}条**

⏰ 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """

        await update.message.reply_text(message, parse_mode='Markdown')

    async def cmd_monitor_stats(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """查看告警统计"""
        # 获取时间范围参数（默认24小时）
        hours = 24
        if context.args and len(context.args) > 0:
            try:
                hours = int(context.args[0])
            except:
                pass

        await update.message.reply_text(f"📊 正在统计过去{hours}小时的数据...")

        stats = await self.reader.get_alert_stats(hours=hours)

        message = f"""
📈 **过去{hours}小时统计**

🔔 总告警数: **{stats['total']}条**

📊 按类型分布:
"""

        for alert_type, count in stats['by_type'].items():
            percentage = (count / stats['total'] * 100) if stats['total'] > 0 else 0
            emoji = self._get_type_emoji(alert_type)
            message += f"  {emoji} {alert_type}: {count}条 ({percentage:.1f}%)\n"

        message += f"\n⚠️ 按级别分布:\n"
        for level, count in stats['by_level'].items():
            percentage = (count / stats['total'] * 100) if stats['total'] > 0 else 0
            emoji = '🚨' if level == 'CRITICAL' else '⚠️' if level == 'WARNING' else 'ℹ️'
            message += f"  {emoji} {level}: {count}条 ({percentage:.1f}%)\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def cmd_recent_alerts(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """查看最近告警"""
        # 获取时间范围参数（默认60分钟）
        minutes = 60
        if context.args and len(context.args) > 0:
            try:
                minutes = int(context.args[0])
            except:
                pass

        await update.message.reply_text(f"🔍 获取最近{minutes}分钟的告警...")

        alerts = await self.reader.get_recent_alerts(minutes=minutes)

        if not alerts:
            await update.message.reply_text(f"✅ 最近{minutes}分钟没有告警")
            return

        message = f"📢 **最近{minutes}分钟告警** (共{len(alerts)}条)\n\n"

        # 只显示前10条
        for i, alert in enumerate(alerts[:10], 1):
            time_str = alert.created_at.strftime('%H:%M:%S')
            emoji = self._get_type_emoji(alert.alert_type)

            message += f"{i}. {emoji} **{alert.symbol}**\n"
            message += f"   类型: {alert.alert_type}\n"
            message += f"   价格: ${alert.price:.4f} ({alert.change_percent:+.2f}%)\n"
            message += f"   时间: {time_str}\n\n"

        if len(alerts) > 10:
            message += f"... 还有 {len(alerts) - 10} 条告警\n"

        await update.message.reply_text(message, parse_mode='Markdown')

    async def cmd_fusion_signals(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """查看高分融合信号"""
        # 获取分数阈值参数（默认85分）
        min_score = 85
        if context.args and len(context.args) > 0:
            try:
                min_score = int(context.args[0])
            except:
                pass

        await update.message.reply_text(f"🎯 搜索≥{min_score}分的融合信号...")

        signals = await self.reader.get_fusion_signals(minutes=30, min_score=min_score)

        if not signals:
            await update.message.reply_text(
                f"暂无≥{min_score}分的融合信号\n\n"
                f"💡 提示: 使用 /fusion_signals 60 可以降低阈值"
            )
            return

        message = f"🟢 **高分融合信号** (≥{min_score}分)\n\n"

        for signal in signals:
            time_str = signal.created_at.strftime('%H:%M:%S')

            message += f"🪙 **{signal.symbol}**\n"
            message += f"📊 评分: **{signal.score}/100**\n"
            message += f"💰 价格: ${signal.price:.4f}\n"
            message += f"⏰ 时间: {time_str}\n"

            # 提取关键信息
            if 'BUY' in signal.message:
                message += f"🎯 建议: **买入信号**\n"
            elif 'WATCH' in signal.message:
                message += f"👀 建议: **观察模式**\n"

            message += f"\n"

        # 添加操作按钮
        keyboard = [
            [
                InlineKeyboardButton("🤖 自动交易", callback_data=f"auto_trade_{min_score}"),
                InlineKeyboardButton("📊 详细分析", callback_data=f"analyze_{min_score}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def cmd_optimize(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """智能优化建议"""
        await update.message.reply_text("🤖 正在分析过去7天的数据...")

        # 获取7天统计
        stats_7d = await self.reader.get_alert_stats(hours=24 * 7)
        stats_24h = await self.reader.get_alert_stats(hours=24)

        # 计算趋势
        daily_avg = stats_7d['total'] / 7
        today_rate = stats_24h['total'] / daily_avg if daily_avg > 0 else 0

        message = f"""
🤖 **智能优化分析**

📊 数据概览:
  • 7天总告警: {stats_7d['total']}条
  • 日均告警: {daily_avg:.1f}条
  • 今日相比: {today_rate:.1%}

💡 优化建议:
"""

        # 生成建议
        if stats_24h['total'] > daily_avg * 1.5:
            message += """
⚠️ **告警过多**
  • 当前告警频率偏高
  • 建议提高阈值 15% → 18%
  • 或增加冷却时间 10min → 15min
"""
        elif stats_24h['total'] < daily_avg * 0.5:
            message += """
⚠️ **告警过少**
  • 可能错过交易机会
  • 建议降低阈值 15% → 12%
  • 或扩大监控币种
"""
        else:
            message += """
✅ **告警频率正常**
  • 当前参数运行良好
  • 建议继续观察
"""

        # 融合信号分析
        fusion_count = stats_24h['by_type'].get('SIGNAL_FUSION', 0)
        message += f"""

🎯 融合信号:
  • 24h融合信号: {fusion_count}条
  • 建议: {'增加融合权重' if fusion_count < 3 else '当前配置合理'}

📈 下一步:
  • 回复 /apply_optimization 应用优化
  • 回复 /backtest 回测新参数
"""

        # 添加操作按钮
        keyboard = [
            [
                InlineKeyboardButton("✅ 应用优化", callback_data="apply_optimization"),
                InlineKeyboardButton("📊 回测", callback_data="backtest")
            ],
            [
                InlineKeyboardButton("❌ 取消", callback_data="cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def cmd_auto_trade(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """自动交易命令"""
        await update.message.reply_text("🤖 检查可交易的高分信号...")

        # 获取最近10分钟的高分信号
        signals = await self.reader.get_fusion_signals(minutes=10, min_score=85)

        if not signals:
            await update.message.reply_text(
                "暂无可交易的高分信号\n\n"
                "💡 当前要求:\n"
                "  • 信号评分 ≥85分\n"
                "  • 时间范围 ≤10分钟\n"
                "  • 包含OI_SPIKE信号"
            )
            return

        message = f"🎯 **发现{len(signals)}个可交易信号**\n\n"

        for i, signal in enumerate(signals, 1):
            message += f"{i}. **{signal.symbol}** - {signal.score}分\n"

        message += f"\n⚠️ **Lana规则提醒:**\n"
        message += f"  • 止损: 亏200 USDT立即平仓\n"
        message += f"  • 持仓: 最长1小时\n"
        message += f"  • 方向: 根据信号决定\n\n"
        message += f"确认执行自动交易吗？"

        # 添加确认按钮
        keyboard = [
            [
                InlineKeyboardButton("✅ 确认交易", callback_data="execute_trade_all"),
                InlineKeyboardButton("❌ 取消", callback_data="cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    async def cmd_help(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """帮助信息"""
        message = """
🤖 **Hermes Monitor Commands**

📊 **查询命令:**
  /monitor_status - 查看监控系统状态
  /monitor_stats [hours] - 查看统计 (默认24h)
  /recent_alerts [minutes] - 最近告警 (默认60min)
  /fusion_signals [score] - 融合信号 (默认≥85分)

🎯 **交易命令:**
  /auto_trade - 基于融合信号自动交易
  /optimize - 智能优化建议

💡 **使用示例:**
  `/monitor_stats 48` - 查看48小时统计
  `/recent_alerts 30` - 查看最近30分钟告警
  `/fusion_signals 80` - 查看≥80分的信号

⚠️ **Lana规则:**
  • 只交易≥85分的融合信号
  • 必须包含OI_SPIKE信号
  • 亏损200 USDT立即止损
  • 持仓时间≤1小时
"""

        await update.message.reply_text(message, parse_mode='Markdown')

    async def handle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ):
        """处理按钮回调"""
        query = update.callback_query
        await query.answer()

        if query.data == "apply_optimization":
            await query.edit_message_text(
                "🔄 正在应用优化配置...\n\n"
                "⚠️ 注意: 此功能需要root权限修改配置文件\n"
                "建议手动执行优化脚本"
            )

        elif query.data == "backtest":
            await query.edit_message_text(
                "📊 回测功能开发中...\n\n"
                "将分析历史数据验证新参数效果"
            )

        elif query.data == "execute_trade_all":
            await query.edit_message_text(
                "🤖 开始执行自动交易...\n\n"
                "⚠️ 此功能需要交易API权限\n"
                "请确保已配置 Binance API Key"
            )

        elif query.data == "cancel":
            await query.edit_message_text("❌ 已取消操作")

        elif query.data.startswith("auto_trade_"):
            min_score = int(query.data.split("_")[2])
            await query.edit_message_text(
                f"🤖 准备交易≥{min_score}分的信号...\n\n"
                f"请使用 /auto_trade 命令确认执行"
            )

        elif query.data.startswith("analyze_"):
            await query.edit_message_text(
                "📊 详细分析功能开发中...\n\n"
                "将展示信号的完整分析报告"
            )

    def _get_type_emoji(self, alert_type: str) -> str:
        """根据告警类型返回emoji"""
        emoji_map = {
            'PRICE_SPIKE': '📈',
            'OI_SPIKE': '🔥',
            'WHALE_ACTIVITY': '🐋',
            'PUMP_DETECTED': '🚀',
            'SIGNAL_FUSION': '🎯',
            'SQUARE_TRENDING': '💬'
        }
        return emoji_map.get(alert_type, '📊')


# 主函数
async def main():
    """启动Telegram Bot"""
    # 替换为你的Telegram Bot Token
    TELEGRAM_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

    bot = HermesMonitorCommands(TELEGRAM_TOKEN)
    await bot.start_bot()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
