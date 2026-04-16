#!/usr/bin/env python3
"""Test Telegram Bot configuration"""

import asyncio
import sys
from dotenv import load_dotenv
import os

load_dotenv()

async def test():
    try:
        from telegram import Bot
        
        token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        print(f"📱 测试 Telegram Bot 配置...")
        print(f"Token: {token[:20]}...{token[-10:]}")
        print(f"Chat ID: {chat_id}\n")
        
        bot = Bot(token=token)
        me = await bot.get_me()
        print(f"✅ Bot 已连接: @{me.username}")
        print(f"   名称: {me.first_name}\n")
        
        await bot.send_message(
            chat_id=int(chat_id),
            text="🎉 <b>配置成功！</b>\n\n你的加密货币监控机器人已经准备就绪！\n\n现在可以运行 <code>./start.sh</code> 启动监控了。",
            parse_mode='HTML'
        )
        
        print(f"✅ 测试消息已发送到 Telegram！")
        print(f"\n🎊 配置完成！运行以下命令启动监控：")
        print(f"   ./start.sh\n")
        
    except Exception as e:
        print(f"❌ 错误: {e}\n")
        print("请检查：")
        print("1. 是否已安装 python-telegram-bot: pip install python-telegram-bot")
        print("2. TELEGRAM_BOT_TOKEN 是否正确")
        print("3. TELEGRAM_CHAT_ID 是否正确")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(test())
