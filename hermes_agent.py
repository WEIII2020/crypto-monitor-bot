#!/usr/bin/env python3
"""
Hermes Agent - Telegram 交互式 Bot

提供双向交互功能：
- 查询实时数据
- 查看信号历史
- 控制策略开关
- 管理交易执行
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

from src.utils.logger import logger
from src.integration.data_bridge import DataBridge
from src.monitoring.health_monitor import HealthMonitor, monitor_loop
from src.monitoring.alert_manager import AlertManager

# 加载环境变量
load_dotenv()


class HermesAgent:
    """Hermes Agent 主类"""

    def __init__(self):
        self.running = False
        self.data_bridge = DataBridge()
        self.app = None

        # 从环境变量读取 Telegram 配置
        self.bot_token = os.getenv('HERMES_BOT_TOKEN') or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')

        # 健康监控
        self.alert_manager = AlertManager(self.bot_token, self.chat_id)
        self.health_monitor = HealthMonitor(alert_callback=self.alert_manager.send_alert)
        self.monitor_task = None

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """启动命令"""
        welcome = """
🤖 **Hermes Agent 已启动**

可用命令：
📊 数据查询：
  /status - 查看系统状态
  /signals [数量] - 查看最近信号
  /price <币种> - 查看实时价格

📈 策略管理：
  /strategies - 查看策略状态

⚙️ 系统管理：
  /help - 查看帮助
  /ping - 测试连接
"""
        await update.message.reply_text(welcome, parse_mode='Markdown')

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """系统状态"""
        try:
            status = await self.data_bridge.get_system_status()

            status_emoji = '🟢' if status['status'] == 'healthy' else '🔴'
            monitor_emoji = '✅' if status.get('monitor_running') else '❌'

            message = f"""
📊 **系统状态**

{status_emoji} 状态: {status['status']}
{monitor_emoji} 监控进程: {'运行中' if status.get('monitor_running') else '已停止'}

⏱ 运行时长: {status['uptime']}
📈 今日信号: {status['signals_today']} 条
💾 内存使用: {status.get('memory_mb', 'N/A')} MB
⚙️ CPU 使用: {status.get('cpu_percent', 'N/A')}%
🎯 监控币种: {status['monitored_symbols']} 个

🕐 更新时间: {datetime.now().strftime('%H:%M:%S')}
"""
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Status command error: {e}")
            await update.message.reply_text(f"❌ 获取状态失败: {e}")

    async def cmd_signals(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """查看信号"""
        try:
            # 解析数量参数
            limit = 5
            if context.args and context.args[0].isdigit():
                limit = min(int(context.args[0]), 20)

            signals = await self.data_bridge.get_latest_signals(limit=limit)

            if not signals:
                await update.message.reply_text("暂无信号数据")
                return

            message = f"📊 **最近 {len(signals)} 条信号**\n\n"
            for i, signal in enumerate(reversed(signals), 1):
                timestamp = signal.get('timestamp', 'N/A')
                msg = signal.get('message', 'N/A')
                message += f"{i}. `{timestamp}`\n   {msg}\n\n"

            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Signals command error: {e}")
            await update.message.reply_text(f"❌ 获取信号失败: {e}")

    async def cmd_price(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """查看价格"""
        try:
            if not context.args:
                await update.message.reply_text("请提供币种符号，例如: /price BTC")
                return

            symbol = context.args[0].upper()
            if not symbol.endswith('USDT'):
                symbol = f"{symbol}USDT"

            price_data = await self.data_bridge.get_realtime_price(symbol)

            if not price_data or price_data.get('price') == 'N/A':
                await update.message.reply_text(f"❌ 无法获取 {symbol} 价格数据")
                return

            message = f"""
💰 **{symbol} 实时价格**

价格: ${price_data['price']}
来源: {price_data.get('source', 'N/A')}
时间: {price_data.get('timestamp', 'N/A')}
"""
            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Price command error: {e}")
            await update.message.reply_text(f"❌ 获取价格失败: {e}")

    async def cmd_strategies(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """策略状态"""
        try:
            strategies = await self.data_bridge.get_strategy_status()

            message = "📈 **策略状态**\n\n"
            for name, info in strategies.items():
                status_emoji = '✅' if info['enabled'] else '❌'
                message += f"{status_emoji} **{name.upper()}**: "
                message += f"{'启用' if info['enabled'] else '禁用'} "
                message += f"(今日: {info['signals_today']} 条)\n"

            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Strategies command error: {e}")
            await update.message.reply_text(f"❌ 获取策略状态失败: {e}")

    async def cmd_ping(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """测试连接"""
        await update.message.reply_text("🏓 Pong! Hermes Agent 运行正常")

    async def cmd_health(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """健康检查"""
        try:
            await update.message.reply_text("🔍 正在运行健康检查...")

            # 运行所有检查
            checks = await self.health_monitor.run_all_checks()
            overall = self.health_monitor.get_overall_status()

            # 构建消息
            status_icon = {
                'healthy': '✅',
                'warning': '⚠️',
                'critical': '🚨',
                'unknown': '❓'
            }

            message = f"""
🏥 **系统健康检查**

{status_icon.get(overall['status'], '📊')} 总体状态: {overall['status'].upper()}
💬 {overall['message']}

📋 **检查详情:**
"""

            for check in checks:
                check_icon = status_icon.get(check.status.value, '❓')
                message += f"\n{check_icon} **{check.name.upper()}**: {check.message}"

            message += f"\n\n⏱ 系统运行时长: {overall['uptime']}"
            message += f"\n🕐 检查时间: {datetime.now().strftime('%H:%M:%S')}"

            await update.message.reply_text(message, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Health command error: {e}")
            await update.message.reply_text(f"❌ 健康检查失败: {e}")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """帮助信息"""
        help_text = """
🤖 **Hermes Agent 命令列表**

📊 **数据查询**
/status - 查看系统状态（运行时长、信号数、资源使用）
/signals [数量] - 查看最近的信号（默认 5 条，最多 20 条）
/price <币种> - 查看实时价格（例如: /price BTC）

📈 **策略管理**
/strategies - 查看所有策略状态

🏥 **监控告警**
/health - 运行系统健康检查

⚙️ **系统管理**
/ping - 测试 Bot 连接
/help - 显示此帮助

💡 **使用提示**
- 命令不区分大小写
- 币种符号自动添加 USDT（BTC → BTCUSDT）
- 所有时间显示为本地时区
- 健康监控每 60 秒自动运行一次
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """错误处理"""
        logger.error(f"Telegram error: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                f"❌ 处理命令时出错: {context.error}"
            )

    async def start(self):
        """启动 Hermes Agent"""
        logger.info("🤖 Starting Hermes Agent...")

        # 检查配置
        if not self.bot_token:
            logger.error("❌ TELEGRAM_BOT_TOKEN 或 HERMES_BOT_TOKEN 未配置")
            logger.error("请在 .env 文件中设置 HERMES_BOT_TOKEN")
            return

        try:
            # 创建 Telegram Application
            self.app = Application.builder().token(self.bot_token).build()

            # 注册命令处理器
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("status", self.cmd_status))
            self.app.add_handler(CommandHandler("signals", self.cmd_signals))
            self.app.add_handler(CommandHandler("price", self.cmd_price))
            self.app.add_handler(CommandHandler("strategies", self.cmd_strategies))
            self.app.add_handler(CommandHandler("health", self.cmd_health))
            self.app.add_handler(CommandHandler("ping", self.cmd_ping))
            self.app.add_handler(CommandHandler("help", self.cmd_help))

            # 注册错误处理器
            self.app.add_error_handler(self.error_handler)

            logger.info("✅ Hermes Agent 命令注册完成")
            logger.info("📱 Telegram Bot 启动中...")

            self.running = True

            # 启动 Bot (使用 polling)
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling()

            logger.info("✅ Hermes Agent started successfully!")
            logger.info(f"📱 Telegram Bot is ready (Token: {self.bot_token[:10]}...)")

            # 初始化告警管理器
            await self.alert_manager.initialize()

            # 启动健康监控循环（后台任务）
            logger.info("🏥 Starting health monitoring...")
            self.monitor_task = asyncio.create_task(monitor_loop(self.health_monitor, interval=60))

            # 发送启动通知
            if self.chat_id:
                try:
                    await self.app.bot.send_message(
                        chat_id=self.chat_id,
                        text="🤖 Hermes Agent 已启动！\n🏥 健康监控已激活\n使用 /help 查看可用命令"
                    )
                except Exception as e:
                    logger.warning(f"Failed to send startup notification: {e}")

            # 保持运行
            try:
                while self.running:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Hermes Agent stopped by user")

        except Exception as e:
            logger.error(f"Failed to start Hermes Agent: {e}")
            raise

    async def stop(self):
        """停止 Hermes Agent"""
        logger.info("🛑 Stopping Hermes Agent...")
        self.running = False

        # 停止监控任务
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

        await self.data_bridge.close()
        await self.alert_manager.close()
        logger.info("✅ Hermes Agent stopped")


async def main():
    agent = HermesAgent()
    try:
        await agent.start()
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
