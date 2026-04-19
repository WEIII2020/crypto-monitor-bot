#!/bin/bash

# 项目合并脚本 - 合并 crypto-monitor-bot 和 Hermes Agent

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "=========================================="
echo "🔄 项目合并 - crypto-monitor-bot + Hermes Agent"
echo "=========================================="

# 设置路径
CRYPTO_BOT_DIR="/Users/lucas/Library/Mobile Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot"
HERMES_DIR="/Users/lucas/Library/Mobile Documents/com~apple~CloudDocs/Cursor/Hermes Agent/hermes-agent"

# 检查目录
if [ ! -d "$CRYPTO_BOT_DIR" ]; then
    error "crypto-monitor-bot 目录不存在"
    exit 1
fi

if [ ! -d "$HERMES_DIR" ]; then
    error "Hermes Agent 目录不存在"
    exit 1
fi

cd "$CRYPTO_BOT_DIR"

# Phase 1: 创建目录结构
info "1️⃣  创建目录结构..."
mkdir -p src/hermes/agent_core
mkdir -p src/hermes/plugins
mkdir -p src/hermes/telegram_bot
mkdir -p src/integration
mkdir -p config/hermes

info "目录创建完成"

# Phase 2: 复制 Hermes Agent 核心文件
info "2️⃣  复制 Hermes Agent 核心..."

# 复制 Agent 核心
if [ -d "$HERMES_DIR/agent" ]; then
    info "复制 agent 核心模块..."
    cp -r "$HERMES_DIR/agent" src/hermes/agent_core/
fi

# 复制 crypto_monitor 工具
if [ -d "$HERMES_DIR/tools/crypto_monitor" ]; then
    info "复制 crypto_monitor 插件..."
    cp -r "$HERMES_DIR/tools/crypto_monitor" src/hermes/plugins/
fi

# 复制配置示例
if [ -f "$HERMES_DIR/.env.example" ]; then
    info "复制 Hermes 配置示例..."
    cp "$HERMES_DIR/.env.example" config/hermes/hermes.env.example
fi

info "Hermes Agent 核心文件复制完成"

# Phase 3: 创建集成层
info "3️⃣  创建集成层..."

# 创建数据桥接文件（占位）
cat > src/integration/__init__.py << 'EOF'
"""
Integration Layer - 集成层

连接 crypto-monitor-bot 和 Hermes Agent
"""
EOF

cat > src/integration/data_bridge.py << 'EOF'
"""
Data Bridge - 数据桥接

提供统一的数据访问接口，让 Hermes Agent 可以读取 crypto-monitor-bot 的数据
"""

from typing import Dict, List, Optional
from datetime import datetime

class DataBridge:
    """数据桥接器"""

    def __init__(self, redis_client=None, postgres_client=None):
        """
        初始化数据桥接器

        Args:
            redis_client: Redis 客户端
            postgres_client: PostgreSQL 客户端
        """
        self.redis = redis_client
        self.postgres = postgres_client

    async def get_latest_signals(self, limit: int = 10) -> List[Dict]:
        """
        获取最近的交易信号

        Args:
            limit: 返回数量

        Returns:
            信号列表
        """
        # TODO: 从数据库读取
        return []

    async def get_signal_by_symbol(self, symbol: str, limit: int = 5) -> List[Dict]:
        """
        获取特定币种的信号历史

        Args:
            symbol: 币种符号
            limit: 返回数量

        Returns:
            信号列表
        """
        # TODO: 实现查询逻辑
        return []

    async def get_realtime_price(self, symbol: str) -> Optional[Dict]:
        """
        获取实时价格

        Args:
            symbol: 币种符号

        Returns:
            价格数据
        """
        # TODO: 从 Redis 读取
        return None

    async def get_system_status(self) -> Dict:
        """
        获取系统状态

        Returns:
            状态信息
        """
        return {
            'status': 'running',
            'uptime': '0d 0h 0m',
            'signals_today': 0,
            'monitored_symbols': 0
        }
EOF

info "集成层创建完成"

# Phase 4: 创建 Hermes Agent 入口
info "4️⃣  创建 Hermes Agent 入口..."

cat > hermes_agent.py << 'EOF'
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
EOF

chmod +x hermes_agent.py

info "Hermes Agent 入口创建完成"

# Phase 5: 创建统一启动脚本
info "5️⃣  创建统一启动脚本..."

cat > run_unified.sh << 'EOF'
#!/bin/bash

# 统一启动脚本 - 同时启动 crypto-monitor-bot 和 Hermes Agent

echo "=========================================="
echo "🚀 启动统一系统"
echo "=========================================="

MODE="${1:-signal}"

echo "运行模式: $MODE"
echo ""

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ 虚拟环境不存在"
    exit 1
fi

# 启动 crypto-monitor-bot（后台）
echo "1️⃣  启动 crypto-monitor-bot..."
python3 main_phase2.py --mode "$MODE" > logs/monitor.log 2>&1 &
MONITOR_PID=$!
echo "   PID: $MONITOR_PID"

# 等待监控系统启动
sleep 3

# 启动 Hermes Agent（前台）
echo "2️⃣  启动 Hermes Agent..."
python3 hermes_agent.py

# 清理
echo ""
echo "停止 crypto-monitor-bot..."
kill $MONITOR_PID 2>/dev/null || true
EOF

chmod +x run_unified.sh

info "统一启动脚本创建完成"

# Phase 6: 更新配置文件
info "6️⃣  更新配置文件..."

cat > config/hermes/hermes_config.yaml << 'EOF'
# Hermes Agent 配置

# Telegram Bot
telegram:
  bot_token: ""  # 从环境变量读取 HERMES_BOT_TOKEN
  enabled: true

  # 命令配置
  commands:
    enabled:
      - status
      - signals
      - price
      - oi
      - strategies
      - positions
      - config
      - logs
      - stats

# 数据桥接
data_bridge:
  redis_host: localhost
  redis_port: 6379
  postgres_host: localhost
  postgres_port: 5432

# 功能开关
features:
  interactive_mode: true      # 交互模式
  auto_response: true         # 自动响应
  command_logging: true       # 命令日志
EOF

info "配置文件更新完成"

# 完成
echo ""
echo "=========================================="
info "✅ 合并完成！"
echo "=========================================="
echo ""
echo "新增文件："
echo "  - src/hermes/               # Hermes Agent 模块"
echo "  - src/integration/          # 集成层"
echo "  - hermes_agent.py           # Hermes 入口"
echo "  - run_unified.sh            # 统一启动"
echo "  - config/hermes/            # Hermes 配置"
echo ""
echo "下一步："
echo "  1. 查看合并方案："
echo "     cat MERGE_PLAN.md"
echo ""
echo "  2. 测试独立运行："
echo "     ./run.sh signal"
echo ""
echo "  3. 测试统一运行："
echo "     ./run_unified.sh"
echo ""
echo "  4. 完善 Hermes Agent 功能："
echo "     vim hermes_agent.py"
echo ""
