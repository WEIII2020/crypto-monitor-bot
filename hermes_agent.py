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
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.logger import logger
from src.integration.data_bridge import DataBridge

class HermesAgent:
    """Hermes Agent 主类"""

    def __init__(self):
        self.running = False
        self.data_bridge = DataBridge()

    async def start(self):
        """启动 Hermes Agent"""
        logger.info("🤖 Starting Hermes Agent...")

        # TODO: 初始化 Telegram Bot
        # TODO: 注册命令处理器
        # TODO: 连接数据桥接器

        self.running = True
        logger.info("✅ Hermes Agent started")

        # 保持运行
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Hermes Agent stopped by user")

    async def stop(self):
        """停止 Hermes Agent"""
        self.running = False
        logger.info("🛑 Hermes Agent stopped")

async def main():
    agent = HermesAgent()
    await agent.start()

if __name__ == "__main__":
    asyncio.run(main())
