#!/bin/bash

# Mac本地服务配置脚本
# 让Bot在Mac上自动启动并保持运行

set -e

PLIST_NAME="com.cryptobot.monitor.plist"
PLIST_SRC="$(pwd)/${PLIST_NAME}"
PLIST_DEST="$HOME/Library/LaunchAgents/${PLIST_NAME}"

echo "🚀 配置Mac本地服务..."
echo ""

# 1. 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先运行: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 2. 检查配置文件
if [ ! -f "config.yaml" ]; then
    echo "❌ 配置文件不存在: config.yaml"
    exit 1
fi

if [ ! -f ".env" ]; then
    echo "⚠️  .env文件不存在，请创建并配置Telegram等信息"
    exit 1
fi

# 3. 创建日志目录
mkdir -p logs

# 4. 检查Redis和PostgreSQL
echo "检查依赖服务..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis未运行，请启动: brew services start redis"
fi

if ! pg_isready -h localhost > /dev/null 2>&1; then
    echo "⚠️  PostgreSQL未运行，请启动: brew services start postgresql"
fi

# 5. 停止已有服务
if launchctl list | grep -q com.cryptobot.monitor; then
    echo "停止已有服务..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# 6. 复制plist文件
echo "安装服务文件..."
cp "$PLIST_SRC" "$PLIST_DEST"

# 7. 加载服务
echo "启动服务..."
launchctl load "$PLIST_DEST"

echo ""
echo "✅ 服务配置完成！"
echo ""
echo "📋 管理命令："
echo "  查看状态: launchctl list | grep cryptobot"
echo "  停止服务: launchctl unload ~/Library/LaunchAgents/${PLIST_NAME}"
echo "  启动服务: launchctl load ~/Library/LaunchAgents/${PLIST_NAME}"
echo "  查看日志: tail -f logs/launchd.log"
echo ""
echo "⚠️  注意："
echo "  - Mac需要保持开机状态"
echo "  - 睡眠模式会暂停服务"
echo "  - 建议：系统偏好设置 > 节能 > 防止自动睡眠（插电源时）"
echo ""
echo "💡 推荐：部署到云服务器以实现真正的24/7运行"
echo "   运行: ./deploy_to_cloud.sh"
