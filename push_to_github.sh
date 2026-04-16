#!/bin/bash

# 加密货币监控Bot - 推送到GitHub私有仓库脚本
# 使用方法：./push_to_github.sh <GitHub仓库URL>
# 示例：./push_to_github.sh https://github.com/yourusername/crypto-monitor-bot.git

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  推送到GitHub私有仓库${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查是否提供了仓库URL
if [ -z "$1" ]; then
    echo -e "${RED}错误：请提供GitHub仓库URL${NC}"
    echo -e "${YELLOW}使用方法：${NC}"
    echo "  ./push_to_github.sh https://github.com/yourusername/crypto-monitor-bot.git"
    echo ""
    echo -e "${YELLOW}步骤：${NC}"
    echo "  1. 访问 https://github.com/new"
    echo "  2. 创建名为 crypto-monitor-bot 的私有仓库"
    echo "  3. 不要初始化README或.gitignore"
    echo "  4. 复制仓库URL，运行此脚本"
    exit 1
fi

REPO_URL="$1"

echo -e "${YELLOW}步骤 1/4：检查Git配置...${NC}"
# 检查git用户配置
if ! git config user.name > /dev/null 2>&1; then
    echo -e "${YELLOW}请设置Git用户名：${NC}"
    read -p "输入你的用户名: " username
    git config user.name "$username"
fi

if ! git config user.email > /dev/null 2>&1; then
    echo -e "${YELLOW}请设置Git邮箱：${NC}"
    read -p "输入你的邮箱: " email
    git config user.email "$email"
fi

echo -e "${GREEN}✓ Git配置完成${NC}"
echo ""

echo -e "${YELLOW}步骤 2/4：添加文件到Git...${NC}"
# 添加所有文件（.gitignore会自动排除敏感文件）
git add .

# 显示将要提交的文件
echo -e "${GREEN}将要提交的文件：${NC}"
git status --short
echo ""

echo -e "${YELLOW}步骤 3/4：创建提交...${NC}"
git commit -m "Initial commit: Crypto Monitor Bot with advanced features

Features:
- Multi-symbol monitoring (BTC, ETH, SOL, etc.)
- Volatility detection and alerts
- Whale activity detection
- Market manipulation detection
- OI (Open Interest) monitoring
- Signal fusion system
- LANA (Large Amount Notification Alert)
- Telegram notifications
- Cloud deployment support (Tencent Cloud, Alibaba Cloud)
- Performance optimization

Deployment:
- Systemd service configuration
- Docker support
- Auto-restart on failure
- Health monitoring

Documentation:
- Complete deployment guides
- System overview
- Configuration examples
- Troubleshooting tips" || echo -e "${YELLOW}注意：可能没有新的更改需要提交${NC}"

echo -e "${GREEN}✓ 提交完成${NC}"
echo ""

echo -e "${YELLOW}步骤 4/4：推送到GitHub...${NC}"
# 配置远程仓库
if git remote get-url origin > /dev/null 2>&1; then
    echo -e "${YELLOW}更新远程仓库地址...${NC}"
    git remote set-url origin "$REPO_URL"
else
    echo -e "${YELLOW}添加远程仓库...${NC}"
    git remote add origin "$REPO_URL"
fi

# 推送到GitHub
echo -e "${YELLOW}正在推送到 $REPO_URL ...${NC}"
git branch -M main
git push -u origin main

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✓ 推送成功！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${GREEN}你的代码已成功推送到GitHub私有仓库！${NC}"
echo -e "${YELLOW}仓库地址：${NC}$REPO_URL"
echo ""
echo -e "${YELLOW}后续操作：${NC}"
echo "  1. 访问GitHub查看你的私有仓库"
echo "  2. 在服务器上可以用 'git clone' 克隆仓库"
echo "  3. 使用 'git pull' 获取最新更新"
echo ""
echo -e "${YELLOW}保持同步：${NC}"
echo "  git add ."
echo "  git commit -m '描述你的更改'"
echo "  git push"
echo ""
