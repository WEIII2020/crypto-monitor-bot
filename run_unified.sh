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
