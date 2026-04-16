#!/usr/bin/env python3
"""
Test Telegram notification with bot status
"""

import asyncio
from src.notifiers.telegram_notifier import TelegramNotifier
from datetime import datetime


async def test_telegram():
    """Send a test status message"""
    notifier = TelegramNotifier()

    # Create a test alert
    test_alert = {
        'symbol': 'SYSTEM',
        'exchange': 'TEST',
        'alert_type': 'STATUS_CHECK',
        'alert_level': 'INFO',
        'price': 0.0,
        'change_percent': 0.0,
        'message': f"""
🤖 监控机器人状态检查

✅ Telegram 推送正常
✅ 正在监控 50 个币种
⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

系统运行中...
        """.strip()
    }

    try:
        await notifier.send_alert(test_alert)
        print("✅ Telegram 测试消息已发送！")
        print("📱 请查看你的 Telegram 是否收到消息")
    except Exception as e:
        print(f"❌ 发送失败: {e}")


if __name__ == '__main__':
    asyncio.run(test_telegram())
