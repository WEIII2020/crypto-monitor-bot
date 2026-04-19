#!/bin/bash

# Crypto Monitor Bot - 腾讯云部署脚本
#
# 使用方法:
#   1. 本地执行: ./deploy.sh
#   2. 服务器上执行: bash deploy.sh server

set -e

echo "=========================================="
echo "🚀 Crypto Monitor Bot - 部署脚本"
echo "=========================================="

# 配置变量（根据您的实际情况修改）
SERVER_HOST="${SERVER_HOST:-your.server.ip}"
SERVER_USER="${SERVER_USER:-root}"
SERVER_PORT="${SERVER_PORT:-22}"
DEPLOY_DIR="/root/crypto-monitor-bot"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否在服务器上运行
if [ "$1" = "server" ]; then
    info "在服务器上执行部署..."

    # 1. 检查 Python 版本
    info "1️⃣  检查 Python 版本..."
    if ! command -v python3 &> /dev/null; then
        error "未安装 Python3，正在安装..."
        yum install -y python3 python3-pip || apt-get install -y python3 python3-pip
    fi
    PYTHON_VERSION=$(python3 --version)
    info "Python 版本: $PYTHON_VERSION"

    # 2. 创建虚拟环境
    info "2️⃣  创建虚拟环境..."
    cd "$DEPLOY_DIR"
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        info "虚拟环境创建成功"
    else
        info "虚拟环境已存在"
    fi

    # 3. 安装依赖
    info "3️⃣  安装依赖..."
    source venv/bin/activate
    pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
    pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    info "依赖安装完成"

    # 4. 配置环境变量
    info "4️⃣  配置环境变量..."
    if [ ! -f ".env" ]; then
        warn ".env 文件不存在，需要手动配置"
        cat > .env.example << 'EOF'
# Telegram 配置（必需）
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export TELEGRAM_CHAT_ID="your_telegram_chat_id"

# Binance API（仅交易模式需要）
export BINANCE_API_KEY="your_binance_api_key"
export BINANCE_API_SECRET="your_binance_api_secret"

# 数据库（可选）
export POSTGRES_PASSWORD="your_postgres_password"
export REDIS_HOST="localhost"
EOF
        warn "请编辑 .env 文件配置您的密钥"
        warn "  vim $DEPLOY_DIR/.env"
    else
        info ".env 文件已存在"
    fi

    # 5. 创建日志目录
    info "5️⃣  创建日志目录..."
    mkdir -p logs
    info "日志目录: $DEPLOY_DIR/logs"

    # 6. 创建 systemd 服务
    info "6️⃣  创建 systemd 服务..."
    cat > /etc/systemd/system/crypto-monitor-bot.service << EOF
[Unit]
Description=Crypto Monitor Bot
After=network.target

[Service]
Type=simple
User=$SERVER_USER
WorkingDirectory=$DEPLOY_DIR
EnvironmentFile=$DEPLOY_DIR/.env
ExecStart=$DEPLOY_DIR/venv/bin/python3 $DEPLOY_DIR/main_phase2.py --mode signal
Restart=always
RestartSec=10
StandardOutput=append:$DEPLOY_DIR/logs/bot.log
StandardError=append:$DEPLOY_DIR/logs/bot.error.log

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    info "systemd 服务创建成功"

    # 7. 显示部署信息
    echo ""
    echo "=========================================="
    info "✅ 服务器部署完成！"
    echo "=========================================="
    echo ""
    info "下一步操作："
    echo "  1. 配置环境变量："
    echo "     vim $DEPLOY_DIR/.env"
    echo ""
    echo "  2. 启动服务："
    echo "     systemctl start crypto-monitor-bot"
    echo ""
    echo "  3. 查看状态："
    echo "     systemctl status crypto-monitor-bot"
    echo ""
    echo "  4. 查看日志："
    echo "     tail -f $DEPLOY_DIR/logs/bot.log"
    echo ""
    echo "  5. 开机自启："
    echo "     systemctl enable crypto-monitor-bot"
    echo ""

    exit 0
fi

# 本地部署逻辑
info "从本地部署到服务器..."

# 1. 检查服务器配置
if [ "$SERVER_HOST" = "your.server.ip" ]; then
    error "请先配置服务器信息！"
    echo ""
    echo "编辑 deploy.sh 文件，修改以下变量："
    echo "  SERVER_HOST=your.server.ip      # 服务器 IP"
    echo "  SERVER_USER=root                 # SSH 用户名"
    echo "  SERVER_PORT=22                   # SSH 端口"
    echo ""
    exit 1
fi

# 2. 测试 SSH 连接
info "1️⃣  测试 SSH 连接..."
if ! ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" "echo 'SSH 连接成功'"; then
    error "SSH 连接失败！"
    echo "请检查："
    echo "  - 服务器 IP 是否正确"
    echo "  - SSH 端口是否正确"
    echo "  - SSH 密钥是否配置"
    exit 1
fi
info "SSH 连接成功"

# 3. 创建远程目录
info "2️⃣  创建远程目录..."
ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" "mkdir -p $DEPLOY_DIR"

# 4. 同步代码
info "3️⃣  同步代码到服务器..."
rsync -avz --progress \
    --exclude 'venv' \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.env' \
    --exclude 'legacy' \
    --exclude 'logs' \
    -e "ssh -p $SERVER_PORT" \
    ./ "$SERVER_USER@$SERVER_HOST:$DEPLOY_DIR/"

info "代码同步完成"

# 5. 在服务器上执行部署
info "4️⃣  在服务器上执行部署脚本..."
ssh -p "$SERVER_PORT" "$SERVER_USER@$SERVER_HOST" "cd $DEPLOY_DIR && bash deploy.sh server"

echo ""
echo "=========================================="
info "✅ 部署完成！"
echo "=========================================="
echo ""
info "下一步："
echo "  1. SSH 登录服务器："
echo "     ssh -p $SERVER_PORT $SERVER_USER@$SERVER_HOST"
echo ""
echo "  2. 配置环境变量："
echo "     vim $DEPLOY_DIR/.env"
echo ""
echo "  3. 启动服务："
echo "     systemctl start crypto-monitor-bot"
echo ""
echo "  4. 查看日志："
echo "     tail -f $DEPLOY_DIR/logs/bot.log"
echo ""
