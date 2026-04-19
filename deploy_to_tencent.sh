#!/bin/bash

# 腾讯云服务器部署脚本
# 使用方法：
#   1. 编辑此文件，填写服务器信息
#   2. 运行: ./deploy_to_tencent.sh

set -e

echo "=========================================="
echo "🚀 部署到腾讯云服务器"
echo "=========================================="

# ============================================
# 📝 请填写您的服务器信息
# ============================================

# 服务器 IP 地址（必需）
SERVER_IP="your_server_ip_here"

# SSH 用户名（默认 root）
SSH_USER="root"

# SSH 端口（默认 22）
SSH_PORT="22"

# 部署目录（默认 /root/crypto-monitor-bot）
DEPLOY_DIR="/root/crypto-monitor-bot"

# ============================================

# 颜色输出
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

# 检查配置
if [ "$SERVER_IP" = "your_server_ip_here" ]; then
    error "请先编辑 deploy_to_tencent.sh 文件，填写服务器 IP 地址！"
    echo ""
    echo "打开文件："
    echo "  vim deploy_to_tencent.sh"
    echo ""
    echo "修改："
    echo "  SERVER_IP=\"your_server_ip_here\"  # 改为实际 IP"
    echo ""
    exit 1
fi

# 测试 SSH 连接
info "1️⃣  测试 SSH 连接..."
if ! ssh -p "$SSH_PORT" "$SSH_USER@$SERVER_IP" "echo 'SSH 连接成功'" 2>/dev/null; then
    error "SSH 连接失败！"
    echo ""
    echo "可能的原因："
    echo "  1. 服务器 IP 地址不正确"
    echo "  2. SSH 端口不正确"
    echo "  3. SSH 密钥未配置"
    echo ""
    echo "配置 SSH 密钥（推荐）："
    echo "  ssh-copy-id -p $SSH_PORT $SSH_USER@$SERVER_IP"
    echo ""
    echo "或手动输入密码继续？(yes/no)"
    read -r confirm
    if [ "$confirm" != "yes" ]; then
        exit 1
    fi
fi

info "SSH 连接成功"
echo ""

# 创建远程目录
info "2️⃣  创建远程目录..."
ssh -p "$SSH_PORT" "$SSH_USER@$SERVER_IP" "mkdir -p $DEPLOY_DIR"

# 同步代码
info "3️⃣  同步代码到服务器..."
echo "   这可能需要几分钟..."
rsync -avz --progress \
    --exclude 'venv' \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'legacy' \
    --exclude 'logs' \
    -e "ssh -p $SSH_PORT" \
    ./ "$SSH_USER@$SERVER_IP:$DEPLOY_DIR/"

info "代码同步完成"
echo ""

# 在服务器上执行部署
info "4️⃣  在服务器上安装依赖和配置服务..."
ssh -p "$SSH_PORT" "$SSH_USER@$SERVER_IP" "cd $DEPLOY_DIR && bash deploy.sh server"

echo ""
echo "=========================================="
info "✅ 部署完成！"
echo "=========================================="
echo ""
info "下一步操作："
echo ""
echo "1️⃣  SSH 登录服务器："
echo "   ssh -p $SSH_PORT $SSH_USER@$SERVER_IP"
echo ""
echo "2️⃣  配置环境变量："
echo "   cd $DEPLOY_DIR"
echo "   vim .env"
echo ""
echo "   必需配置："
echo "   export TELEGRAM_BOT_TOKEN=\"your_bot_token\""
echo "   export TELEGRAM_CHAT_ID=\"your_chat_id\""
echo ""
echo "3️⃣  启动服务："
echo "   systemctl start crypto-monitor-bot"
echo "   systemctl status crypto-monitor-bot"
echo ""
echo "4️⃣  查看日志："
echo "   tail -f $DEPLOY_DIR/logs/bot.log"
echo ""
echo "5️⃣  开机自启："
echo "   systemctl enable crypto-monitor-bot"
echo ""
echo "6️⃣  使用管理脚本："
echo "   cd $DEPLOY_DIR"
echo "   ./manage.sh status   # 查看状态"
echo "   ./manage.sh logs     # 查看日志"
echo "   ./manage.sh restart  # 重启服务"
echo ""

# 提供快捷 SSH 命令
info "💡 快捷命令："
echo "   alias tencent='ssh -p $SSH_PORT $SSH_USER@$SERVER_IP'"
echo "   (将此行添加到 ~/.bashrc 或 ~/.zshrc)"
echo ""
