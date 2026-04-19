#!/bin/bash

# 统一启动脚本 - 带健康监控

echo "=========================================="
echo "🚀 启动统一系统（含监控）"
echo "=========================================="

MODE="${1:-signal}"

echo "运行模式: $MODE"
echo "监控功能: 已启用"
echo ""

# 激活虚拟环境
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ 虚拟环境不存在，请先运行: python3 -m venv venv"
    exit 1
fi

# 检查配置
if [ ! -f ".env" ]; then
    echo "⚠️  警告: .env 文件不存在"
    echo "   某些功能可能无法使用"
fi

# 创建日志目录
mkdir -p logs

# 启动 crypto-monitor-bot（后台）
echo "1️⃣  启动 crypto-monitor-bot..."
python3 main_phase2.py --mode "$MODE" > logs/monitor.log 2>&1 &
MONITOR_PID=$!
echo "   PID: $MONITOR_PID"

# 等待监控系统启动
echo "   等待启动..."
sleep 5

# 检查进程是否存活
if ! ps -p $MONITOR_PID > /dev/null; then
    echo "❌ crypto-monitor-bot 启动失败"
    echo "   查看日志: tail -f logs/monitor.log"
    exit 1
fi

echo "   ✅ crypto-monitor-bot 启动成功"
echo ""

# 启动 Hermes Agent（前台）
echo "2️⃣  启动 Hermes Agent（含健康监控）..."
echo "   Telegram Bot 将提供交互式命令"
echo "   健康监控每分钟自动检查一次"
echo ""

# 捕获退出信号
trap "echo ''; echo '停止所有服务...'; kill $MONITOR_PID 2>/dev/null; exit 0" SIGINT SIGTERM

# 启动 Hermes Agent（会一直运行）
python3 hermes_agent.py

# 清理（如果正常退出）
echo ""
echo "停止 crypto-monitor-bot..."
kill $MONITOR_PID 2>/dev/null || true

echo "✅ 所有服务已停止"
