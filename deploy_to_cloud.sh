#!/bin/bash

# 🚀 Crypto Monitor Bot - 自动部署到云服务器
# 使用方法: ./deploy_to_cloud.sh

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  Crypto Monitor Bot - 云端部署工具${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查本地环境
echo -e "${YELLOW}检查本地环境...${NC}"
if ! command -v ssh &> /dev/null; then
    echo -e "${RED}错误: 未安装ssh命令${NC}"
    exit 1
fi

if ! command -v scp &> /dev/null; then
    echo -e "${RED}错误: 未安装scp命令${NC}"
    exit 1
fi

# 获取服务器信息
echo ""
echo -e "${YELLOW}请输入服务器信息:${NC}"
read -p "服务器IP地址: " SERVER_IP
read -p "SSH端口 (默认22): " SSH_PORT
SSH_PORT=${SSH_PORT:-22}
read -p "SSH用户名 (默认root): " SSH_USER
SSH_USER=${SSH_USER:-root}

echo ""
echo -e "${YELLOW}请选择操作系统:${NC}"
echo "1) Ubuntu 20.04/22.04 (推荐)"
echo "2) CentOS 7/8"
read -p "选择 (1-2): " OS_CHOICE

# 设置SSH连接字符串
SSH_HOST="${SSH_USER}@${SERVER_IP}"
SSH_CMD="ssh -p ${SSH_PORT} ${SSH_HOST}"
SCP_CMD="scp -P ${SSH_PORT}"

# 测试连接
echo ""
echo -e "${YELLOW}测试服务器连接...${NC}"
if ! $SSH_CMD "echo '连接成功'" &> /dev/null; then
    echo -e "${RED}无法连接到服务器 ${SERVER_IP}:${SSH_PORT}${NC}"
    echo "请检查:"
    echo "  1. IP地址和端口是否正确"
    echo "  2. 服务器是否开启"
    echo "  3. 防火墙是否允许SSH连接"
    echo "  4. SSH密钥或密码是否正确"
    exit 1
fi
echo -e "${GREEN}✓ 连接成功${NC}"

# 确认部署
echo ""
echo -e "${YELLOW}将要部署到:${NC}"
echo "  服务器: ${SERVER_IP}:${SSH_PORT}"
echo "  用户: ${SSH_USER}"
echo "  系统: $([ "$OS_CHOICE" == "1" ] && echo "Ubuntu" || echo "CentOS")"
echo ""
read -p "确认开始部署? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "已取消部署"
    exit 0
fi

# 打包代码
echo ""
echo -e "${BLUE}[1/8] 打包项目代码...${NC}"
TEMP_DIR=$(mktemp -d)
echo "临时目录: $TEMP_DIR"

# 复制文件到临时目录，排除不需要的文件
rsync -av --progress \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='logs/*.log' \
    --exclude='.git' \
    --exclude='bot.pid' \
    --exclude='*.tar.gz' \
    ./ "${TEMP_DIR}/crypto-monitor-bot/"

# 创建tar包
cd "$TEMP_DIR"
tar -czf crypto-monitor-bot.tar.gz crypto-monitor-bot/
echo -e "${GREEN}✓ 代码打包完成${NC}"

# 上传代码
echo ""
echo -e "${BLUE}[2/8] 上传代码到服务器...${NC}"
$SCP_CMD "${TEMP_DIR}/crypto-monitor-bot.tar.gz" "${SSH_HOST}:/tmp/"
echo -e "${GREEN}✓ 上传完成${NC}"

# 清理临时文件
rm -rf "$TEMP_DIR"

# 在服务器上执行部署脚本
echo ""
echo -e "${BLUE}[3/8] 安装系统依赖...${NC}"

$SSH_CMD "bash -s" << 'ENDSSH'
set -e

# 检测操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    echo "无法检测操作系统"
    exit 1
fi

echo "检测到操作系统: $OS"

# 安装依赖
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    echo "更新软件包..."
    apt-get update -qq

    echo "安装基础工具..."
    apt-get install -y -qq git curl wget vim unzip > /dev/null

    echo "安装Python 3.9+..."
    apt-get install -y -qq python3 python3-pip python3-venv > /dev/null

    echo "安装Redis..."
    apt-get install -y -qq redis-server > /dev/null
    systemctl start redis-server
    systemctl enable redis-server > /dev/null 2>&1

    echo "安装PostgreSQL..."
    apt-get install -y -qq postgresql postgresql-contrib > /dev/null
    systemctl start postgresql
    systemctl enable postgresql > /dev/null 2>&1

elif [ "$OS" = "centos" ] || [ "$OS" = "rhel" ]; then
    echo "更新软件包..."
    yum update -y -q

    echo "安装基础工具..."
    yum install -y -q git curl wget vim unzip

    echo "安装Python 3.9..."
    yum install -y -q python39 python39-pip

    echo "安装Redis..."
    yum install -y -q redis
    systemctl start redis
    systemctl enable redis > /dev/null 2>&1

    echo "安装PostgreSQL..."
    yum install -y -q postgresql-server postgresql-contrib
    postgresql-setup initdb > /dev/null 2>&1 || true
    systemctl start postgresql
    systemctl enable postgresql > /dev/null 2>&1
else
    echo "不支持的操作系统: $OS"
    exit 1
fi

echo "✓ 系统依赖安装完成"
ENDSSH

echo -e "${GREEN}✓ 系统依赖安装完成${NC}"

# 配置PostgreSQL
echo ""
echo -e "${BLUE}[4/8] 配置PostgreSQL...${NC}"

# 生成随机密码
PG_PASSWORD=$(openssl rand -base64 12 | tr -d "=+/" | cut -c1-16)

$SSH_CMD "bash -s" << ENDSSH
set -e

# 创建数据库用户和数据库
sudo -u postgres psql << 'EOPSQL'
-- 删除已存在的用户和数据库（如果有）
DROP DATABASE IF EXISTS crypto_monitor;
DROP USER IF EXISTS cryptobot;

-- 创建新用户和数据库
CREATE USER cryptobot WITH PASSWORD '${PG_PASSWORD}';
CREATE DATABASE crypto_monitor OWNER cryptobot;
GRANT ALL PRIVILEGES ON DATABASE crypto_monitor TO cryptobot;
EOPSQL

echo "✓ PostgreSQL配置完成"
echo "数据库密码: ${PG_PASSWORD}"
ENDSSH

echo -e "${GREEN}✓ PostgreSQL配置完成${NC}"

# 部署代码
echo ""
echo -e "${BLUE}[5/8] 部署应用代码...${NC}"

$SSH_CMD "bash -s" << 'ENDSSH'
set -e

# 解压代码
cd /opt
if [ -d "crypto-monitor-bot" ]; then
    echo "备份旧版本..."
    mv crypto-monitor-bot crypto-monitor-bot.backup.$(date +%Y%m%d_%H%M%S)
fi

tar -xzf /tmp/crypto-monitor-bot.tar.gz
rm /tmp/crypto-monitor-bot.tar.gz

# 创建虚拟环境
cd /opt/crypto-monitor-bot
echo "创建Python虚拟环境..."
python3 -m venv venv

# 安装依赖
echo "安装Python依赖包..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo "✓ 应用代码部署完成"
ENDSSH

echo -e "${GREEN}✓ 应用代码部署完成${NC}"

# 配置环境变量
echo ""
echo -e "${BLUE}[6/8] 配置环境变量...${NC}"

# 检查本地.env文件
if [ ! -f ".env" ]; then
    echo -e "${RED}错误: 本地未找到 .env 文件${NC}"
    echo "请先在本地创建 .env 文件并配置 Telegram Bot Token 和 Chat ID"
    exit 1
fi

# 读取Telegram配置
TELEGRAM_BOT_TOKEN=$(grep "TELEGRAM_BOT_TOKEN" .env | cut -d '=' -f2)
TELEGRAM_CHAT_ID=$(grep "TELEGRAM_CHAT_ID" .env | cut -d '=' -f2)

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
    echo -e "${RED}错误: .env 文件中缺少 Telegram 配置${NC}"
    exit 1
fi

# 上传.env文件（使用服务器的PostgreSQL密码）
$SSH_CMD "cat > /opt/crypto-monitor-bot/.env" << ENDENV
# Telegram配置
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# PostgreSQL配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=crypto_monitor
POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=${PG_PASSWORD}

# 监控配置
MAX_SYMBOLS=50
CHECK_INTERVAL=30
ENDENV

echo -e "${GREEN}✓ 环境变量配置完成${NC}"

# 配置systemd服务
echo ""
echo -e "${BLUE}[7/8] 配置系统服务...${NC}"

$SSH_CMD "cat > /etc/systemd/system/crypto-monitor.service" << 'ENDSERVICE'
[Unit]
Description=Crypto Monitor Bot
After=network.target redis.service postgresql.service
Wants=redis.service postgresql.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/crypto-monitor-bot
Environment="PATH=/opt/crypto-monitor-bot/venv/bin"
ExecStart=/opt/crypto-monitor-bot/venv/bin/python /opt/crypto-monitor-bot/main.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/crypto-monitor-bot/logs/systemd.log
StandardError=append:/opt/crypto-monitor-bot/logs/systemd-error.log

[Install]
WantedBy=multi-user.target
ENDSERVICE

$SSH_CMD "bash -s" << 'ENDSSH'
# 重载systemd
systemctl daemon-reload

# 启动服务
systemctl start crypto-monitor

# 设置开机自启
systemctl enable crypto-monitor

echo "✓ 系统服务配置完成"
ENDSSH

echo -e "${GREEN}✓ 系统服务配置完成${NC}"

# 验证部署
echo ""
echo -e "${BLUE}[8/8] 验证部署状态...${NC}"
sleep 5  # 等待服务启动

$SSH_CMD "bash -s" << 'ENDSSH'
set -e

echo "检查服务状态..."
if systemctl is-active --quiet crypto-monitor; then
    echo "✓ 服务运行中"
else
    echo "✗ 服务未运行"
    systemctl status crypto-monitor --no-pager
    exit 1
fi

echo ""
echo "检查Redis..."
if redis-cli ping > /dev/null 2>&1; then
    echo "✓ Redis运行正常"
else
    echo "✗ Redis连接失败"
fi

echo ""
echo "检查PostgreSQL..."
if pg_isready -h localhost > /dev/null 2>&1; then
    echo "✓ PostgreSQL运行正常"
else
    echo "✗ PostgreSQL连接失败"
fi

echo ""
echo "最近的日志:"
tail -10 /opt/crypto-monitor-bot/logs/crypto_monitor_$(date +%Y-%m-%d).log 2>/dev/null || echo "日志文件尚未生成，请等待..."

ENDSSH

# 部署完成
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  🎉 部署成功！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}服务器信息:${NC}"
echo "  IP: ${SERVER_IP}"
echo "  端口: ${SSH_PORT}"
echo ""
echo -e "${YELLOW}PostgreSQL密码:${NC}"
echo "  ${PG_PASSWORD}"
echo "  ${RED}请妥善保管此密码！${NC}"
echo ""
echo -e "${YELLOW}常用管理命令:${NC}"
echo "  查看状态: ssh -p ${SSH_PORT} ${SSH_HOST} 'systemctl status crypto-monitor'"
echo "  查看日志: ssh -p ${SSH_PORT} ${SSH_HOST} 'journalctl -u crypto-monitor -f'"
echo "  重启服务: ssh -p ${SSH_PORT} ${SSH_HOST} 'systemctl restart crypto-monitor'"
echo "  停止服务: ssh -p ${SSH_PORT} ${SSH_HOST} 'systemctl stop crypto-monitor'"
echo ""
echo -e "${YELLOW}下一步:${NC}"
echo "  1. 等待5-10分钟，Bot会开始接收数据"
echo "  2. 在Telegram中应该会收到测试通知"
echo "  3. 查看服务器日志确认运行正常"
echo ""
echo "详细文档: DEPLOYMENT_GUIDE.md"
echo ""
