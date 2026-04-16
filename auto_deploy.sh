#!/bin/bash
#
# 自动部署脚本 - 预配置版本
# 腾讯云服务器: 119.28.43.237
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示欢迎信息
clear
echo -e "${BLUE}"
cat << "EOF"
╔═══════════════════════════════════════════╗
║                                           ║
║   Crypto Monitor Bot                      ║
║   自动部署脚本 - 预配置版本               ║
║                                           ║
╚═══════════════════════════════════════════╝
EOF
echo -e "${NC}"

print_header "第一步：确认配置信息"

echo "服务器IP: 119.28.43.237"
echo "Telegram Bot Token: 8612731213:AAE...T68"
echo "PostgreSQL 密码: P@ssw0rd2024!Crypto#DB"
echo "Redis 密码: R3dis\$Secure#2024Pass!"
echo ""

# 获取 Chat ID
while true; do
    read -p "请输入你的 Telegram Chat ID (纯数字): " CHAT_ID

    if [[ "$CHAT_ID" =~ ^[0-9]+$ ]]; then
        echo ""
        print_info "Chat ID: $CHAT_ID"
        read -p "确认正确？(y/n): " confirm
        if [ "$confirm" = "y" ]; then
            break
        fi
    else
        print_error "Chat ID 必须是纯数字！"
        echo "获取方法: 在浏览器打开下面的链接"
        echo "https://api.telegram.org/bot8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68/getUpdates"
        echo ""
    fi
done

print_header "第二步：解压项目代码"

print_info "创建项目目录..."
mkdir -p /opt/crypto-monitor-bot

if [ -f /root/crypto-bot.tar.gz ]; then
    print_info "解压项目代码..."
    tar -xzf /root/crypto-bot.tar.gz -C /opt/crypto-monitor-bot/
    print_success "代码解压完成"
else
    print_error "未找到代码包: /root/crypto-bot.tar.gz"
    print_info "请先从本地上传代码包"
    exit 1
fi

print_header "第三步：更新系统并安装依赖"

print_info "更新软件包列表..."
apt update -y

print_info "安装 Python、PostgreSQL、Redis 等依赖..."
apt install -y python3.9 python3.9-venv python3-pip \
               postgresql postgresql-contrib \
               redis-server supervisor \
               htop curl wget vim

print_success "依赖安装完成"

print_header "第四步：配置 PostgreSQL"

print_info "创建数据库用户和数据库..."

sudo -u postgres psql << 'PSQL_EOF'
DROP DATABASE IF EXISTS crypto_monitor;
DROP USER IF EXISTS cryptobot;
CREATE USER cryptobot WITH PASSWORD 'P@ssw0rd2024!Crypto#DB';
CREATE DATABASE crypto_monitor OWNER cryptobot;
GRANT ALL PRIVILEGES ON DATABASE crypto_monitor TO cryptobot;
PSQL_EOF

print_info "配置访问权限..."
PG_HBA=$(find /etc/postgresql -name pg_hba.conf | head -1)
if ! grep -q "127.0.0.1/32.*md5" "$PG_HBA"; then
    echo "host    all    all    127.0.0.1/32    md5" >> "$PG_HBA"
fi

print_info "重启 PostgreSQL..."
systemctl restart postgresql
systemctl enable postgresql

print_success "PostgreSQL 配置完成"

print_header "第五步：配置 Redis"

print_info "设置 Redis 密码..."

# 备份配置
cp /etc/redis/redis.conf /etc/redis/redis.conf.backup

# 设置密码 (注意特殊字符转义)
REDIS_PASS='R3dis$Secure#2024Pass!'
sed -i "s/^# requirepass.*/requirepass $REDIS_PASS/" /etc/redis/redis.conf
sed -i "s/^requirepass.*/requirepass $REDIS_PASS/" /etc/redis/redis.conf

# 确保只监听本地
sed -i "s/^bind .*/bind 127.0.0.1/" /etc/redis/redis.conf

print_info "重启 Redis..."
systemctl restart redis
systemctl enable redis

print_success "Redis 配置完成"

print_header "第六步：安装 Python 依赖"

cd /opt/crypto-monitor-bot

print_info "创建 Python 虚拟环境..."
python3.9 -m venv venv

print_info "安装依赖包..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

print_success "Python 依赖安装完成"

print_header "第七步：配置环境变量"

print_info "创建 .env 配置文件..."

cat > .env << ENV_EOF
# Telegram Bot
TELEGRAM_BOT_TOKEN=8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68
TELEGRAM_CHAT_ID=$CHAT_ID

# Database
POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=P@ssw0rd2024!Crypto#DB
POSTGRES_DB=crypto_monitor
DATABASE_URL=postgresql://cryptobot:P@ssw0rd2024!Crypto#DB@localhost:5432/crypto_monitor

# Redis
REDIS_PASSWORD=R3dis\$Secure#2024Pass!
REDIS_URL=redis://:R3dis\$Secure#2024Pass!@localhost:6379/0

# Logging
LOG_LEVEL=INFO
ENV_EOF

chmod 600 .env

print_success "配置文件创建完成"

print_header "第八步：测试运行"

print_info "测试运行 15 秒..."
print_warning "如果看到错误，请按 Ctrl+C 停止"
echo ""

timeout 15 venv/bin/python main.py || true

echo ""
read -p "是否看到 '✅ Bot is running!' 消息？(y/n): " test_ok

if [ "$test_ok" != "y" ]; then
    print_error "测试失败，请检查日志"
    print_info "手动运行查看详细错误:"
    print_info "cd /opt/crypto-monitor-bot && source venv/bin/activate && python main.py"
    exit 1
fi

print_success "测试运行成功"

print_header "第九步：配置开机自启动"

print_info "创建 Supervisor 配置..."

cat > /etc/supervisor/conf.d/crypto-monitor-bot.conf << 'SUPERVISOR_EOF'
[program:crypto-monitor-bot]
directory=/opt/crypto-monitor-bot
command=/opt/crypto-monitor-bot/venv/bin/python main.py
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/crypto-monitor-bot.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
environment=PATH="/opt/crypto-monitor-bot/venv/bin"
SUPERVISOR_EOF

print_info "启动服务..."
supervisorctl reread
supervisorctl update
supervisorctl start crypto-monitor-bot

sleep 3

print_info "检查服务状态..."
supervisorctl status crypto-monitor-bot

print_success "Supervisor 配置完成"

print_header "第十步：配置防火墙"

print_info "安装并配置 UFW 防火墙..."
apt install -y ufw

print_info "配置防火墙规则..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp

print_warning "启用防火墙..."
ufw --force enable

print_success "防火墙配置完成"

print_header "第十一步：发送测试消息"

print_info "发送 Telegram 测试消息..."

cd /opt/crypto-monitor-bot
source venv/bin/activate

python3 << 'TEST_EOF'
import asyncio
from dotenv import load_dotenv
from src.notifiers.telegram_notifier import TelegramNotifier

load_dotenv()

async def test():
    try:
        notifier = TelegramNotifier()
        await notifier.send_message("🎉 部署成功！\n\n✅ 服务器: 119.28.43.237\n✅ 监控已启动\n✅ 开始监控 50+ 加密货币\n\n等待价格波动时会收到告警 📊")
        print("✅ 测试消息已发送")
    except Exception as e:
        print(f"❌ 发送失败: {e}")

asyncio.run(test())
TEST_EOF

print_header "部署完成！"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  🎉 部署成功！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${BLUE}服务器信息:${NC}"
echo "  IP: 119.28.43.237"
echo "  项目目录: /opt/crypto-monitor-bot"
echo ""
echo -e "${BLUE}常用命令:${NC}"
echo "  查看状态: supervisorctl status"
echo "  查看日志: tail -f /var/log/crypto-monitor-bot.log"
echo "  重启服务: supervisorctl restart crypto-monitor-bot"
echo ""
echo -e "${BLUE}下一步:${NC}"
echo "  1. 查看实时日志确认运行正常"
echo "  2. 在 Telegram 查看测试消息"
echo "  3. 等待价格波动时会收到告警"
echo ""
echo -e "${YELLOW}重要提醒:${NC}"
echo "  - 已配置开机自启动"
echo "  - 日志位置: /var/log/crypto-monitor-bot.log"
echo "  - 修改配置后需重启: supervisorctl restart crypto-monitor-bot"
echo ""
echo -e "${GREEN}========================================${NC}"
echo ""

print_success "现在可以查看日志了: tail -f /var/log/crypto-monitor-bot.log"
