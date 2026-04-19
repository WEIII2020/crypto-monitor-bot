#!/bin/bash

# 快速启动脚本 - 检查配置并启动系统

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
}

title() {
    echo -e "${BLUE}$1${NC}"
}

echo ""
title "=========================================="
title "🚀 Crypto Monitor Bot - 快速启动"
title "=========================================="
echo ""

# 1. 检查虚拟环境
title "1️⃣  检查虚拟环境..."
if [ ! -d "venv" ]; then
    error "虚拟环境不存在"
    echo ""
    echo "请先创建虚拟环境："
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi
info "虚拟环境存在"

# 2. 检查配置文件
title "2️⃣  检查配置文件..."
if [ ! -f "config/config.yaml" ]; then
    error "配置文件不存在"
    exit 1
fi
info "配置文件存在"

# 3. 检查环境变量（可选）
title "3️⃣  检查环境变量..."
if [ -f ".env" ]; then
    source .env
    info ".env 文件已加载"
else
    warn ".env 文件不存在（Telegram 通知可能不工作）"
fi

if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    info "TELEGRAM_BOT_TOKEN 已配置"
else
    warn "TELEGRAM_BOT_TOKEN 未配置"
fi

# 4. 选择运行模式
title "4️⃣  选择运行模式..."
echo ""
echo "可用模式："
echo "  1) monitor  - 只监控数据采集"
echo "  2) signal   - 监控 + 信号生成（推荐）"
echo "  3) unified  - 监控 + 信号 + Hermes Agent（完整功能）"
echo "  4) trade    - 监控 + 信号 + 自动交易（谨慎）"
echo ""

read -p "请选择模式 [1-4] (默认: 2): " choice
choice=${choice:-2}

case $choice in
    1)
        MODE="monitor"
        UNIFIED=false
        ;;
    2)
        MODE="signal"
        UNIFIED=false
        ;;
    3)
        MODE="signal"
        UNIFIED=true
        ;;
    4)
        MODE="trade"
        UNIFIED=false
        warn "⚠️  交易模式已选择，请确认已配置 Binance API"
        read -p "确认继续? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            echo "已取消"
            exit 0
        fi
        ;;
    *)
        error "无效选择"
        exit 1
        ;;
esac

echo ""
info "运行模式: $MODE"
if [ "$UNIFIED" = true ]; then
    info "Hermes Agent: 已启用"
fi
echo ""

# 5. 创建日志目录
mkdir -p logs

# 6. 启动系统
title "5️⃣  启动系统..."
echo ""

source venv/bin/activate

if [ "$UNIFIED" = true ]; then
    # 统一模式
    info "启动 crypto-monitor-bot (后台)..."
    nohup python3 main_phase2.py --mode "$MODE" > logs/monitor.log 2>&1 &
    MONITOR_PID=$!
    echo "   PID: $MONITOR_PID"
    
    sleep 3
    
    info "启动 Hermes Agent (前台)..."
    echo ""
    echo "================================================"
    echo "系统已启动！"
    echo "================================================"
    echo "监控 Bot PID: $MONITOR_PID"
    echo "日志文件: logs/monitor.log"
    echo ""
    echo "按 Ctrl+C 停止系统"
    echo "================================================"
    echo ""
    
    # 启动 Hermes Agent（前台）
    python3 hermes_agent.py
    
    # 清理
    echo ""
    info "停止 crypto-monitor-bot..."
    kill $MONITOR_PID 2>/dev/null || true
    
else
    # 独立模式
    info "启动 crypto-monitor-bot..."
    echo ""
    echo "================================================"
    echo "系统已启动！"
    echo "================================================"
    echo "运行模式: $MODE"
    echo "日志文件: logs/bot.log"
    echo ""
    echo "按 Ctrl+C 停止系统"
    echo "================================================"
    echo ""
    
    python3 main_phase2.py --mode "$MODE"
fi
