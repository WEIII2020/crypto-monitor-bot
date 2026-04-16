#!/bin/bash
#
# 上传代码到腾讯云服务器
#

set -e

SERVER_IP="119.28.43.237"
PROJECT_DIR="/Users/szld2403203/Library/Mobile Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot"

echo "================================================"
echo "上传项目到腾讯云服务器"
echo "服务器IP: $SERVER_IP"
echo "================================================"
echo ""

cd "$PROJECT_DIR"

echo "📦 打包项目文件..."
tar -czf crypto-bot.tar.gz \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='venv' \
  --exclude='.env' \
  --exclude='bot.pid' \
  --exclude='.DS_Store' \
  --exclude='*.log' \
  .

echo "✅ 打包完成: crypto-bot.tar.gz"
echo ""

echo "📤 上传代码包到服务器..."
scp crypto-bot.tar.gz root@$SERVER_IP:/root/

echo "📤 上传部署脚本..."
scp deploy_tencent_cloud.sh root@$SERVER_IP:/root/

echo "📤 上传快速部署命令..."
scp QUICK_DEPLOY_COMMANDS.md root@$SERVER_IP:/root/

echo ""
echo "================================================"
echo "✅ 上传完成！"
echo "================================================"
echo ""
echo "下一步："
echo "1. 连接到服务器: ssh root@$SERVER_IP"
echo "2. 运行部署脚本: bash /root/deploy_tencent_cloud.sh"
echo ""

# 清理本地打包文件
rm crypto-bot.tar.gz

echo "💡 提示: 现在可以连接到服务器进行部署了"
echo ""
