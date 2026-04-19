#!/bin/bash

# Crypto Monitor Bot - 启动脚本

set -e

echo "=========================================="
echo "🚀 Crypto Monitor Bot"
echo "=========================================="

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✅ Python 版本: $PYTHON_VERSION"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python3 -m venv venv"
    exit 1
fi

# 激活虚拟环境
echo "🔧 激活虚拟环境..."
source venv/bin/activate

# 检查依赖
echo "📦 检查依赖..."
python3 -m pip install -q -r requirements.txt 2>/dev/null || echo "⚠️  跳过依赖检查"

# 解析命令行参数
MODE="${1:-signal}"  # 默认 signal 模式
CONFIG="${2:-config/config.yaml}"

# 验证模式
if [[ ! "$MODE" =~ ^(monitor|signal|trade)$ ]]; then
    echo "❌ 无效的模式: $MODE"
    echo "   支持的模式: monitor, signal, trade"
    exit 1
fi

# 显示运行信息
echo ""
echo "🎯 运行模式: $MODE"
echo "📝 配置文件: $CONFIG"
echo ""

# 启动 Bot
case "$MODE" in
    monitor)
        echo "📊 启动监控模式（只采集数据）..."
        ;;
    signal)
        echo "🎯 启动信号模式（监控+信号生成）..."
        ;;
    trade)
        echo "💰 启动交易模式（监控+信号+自动交易）..."
        echo "⚠️  警告: 自动交易已启用！"
        read -p "   确认继续? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            echo "❌ 已取消"
            exit 0
        fi
        ;;
esac

echo ""
echo "🚀 正在启动..."
echo "   按 Ctrl+C 停止"
echo ""

# 运行主程序
python3 main_phase2.py --mode "$MODE" --config "$CONFIG"
