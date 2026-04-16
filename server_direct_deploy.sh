#!/bin/bash
#
# 在服务器上直接部署（不需要 Git）
# 此脚本会创建所有必要的文件
#

set -e

echo "🚀 开始直接部署（不使用 Git）..."

# 1. 安装依赖
echo "📦 安装系统依赖..."
apt update -qq
apt install -y python3.9 python3.9-venv python3-pip \
               postgresql postgresql-contrib \
               redis-server supervisor htop curl wget

# 2. 配置 PostgreSQL
echo "🗄️ 配置 PostgreSQL..."
sudo -u postgres psql << 'PSQL_EOF'
DROP DATABASE IF EXISTS crypto_monitor;
DROP USER IF EXISTS cryptobot;
CREATE USER cryptobot WITH PASSWORD 'P@ssw0rd2024!Crypto#DB';
CREATE DATABASE crypto_monitor OWNER cryptobot;
GRANT ALL PRIVILEGES ON DATABASE crypto_monitor TO cryptobot;
\q
PSQL_EOF

PG_HBA=$(find /etc/postgresql -name pg_hba.conf | head -1)
if ! grep -q "127.0.0.1/32.*md5" "$PG_HBA"; then
    echo "host all all 127.0.0.1/32 md5" >> "$PG_HBA"
fi
systemctl restart postgresql && systemctl enable postgresql

# 3. 配置 Redis
echo "💾 配置 Redis..."
sed -i 's/# requirepass.*/requirepass R3dis$Secure#2024Pass!/' /etc/redis/redis.conf
sed -i 's/^bind .*/bind 127.0.0.1/' /etc/redis/redis.conf
systemctl restart redis && systemctl enable redis

# 4. 创建项目目录
echo "📁 创建项目目录结构..."
mkdir -p /opt/crypto-monitor-bot/src/{collectors,analyzers,notifiers,database,utils}

cd /opt/crypto-monitor-bot

# 提示用户需要上传代码
echo ""
echo "⚠️  现在需要上传项目代码文件"
echo ""
echo "请在本地 Mac 执行以下命令上传代码:"
echo ""
echo 'cd "/Users/szld2403203/Library/Mobile Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot"'
echo ""
echo "# 打包代码"
echo "tar -czf crypto-bot.tar.gz \\"
echo "  --exclude='.git' \\"
echo "  --exclude='__pycache__' \\"
echo "  --exclude='venv' \\"
echo "  --exclude='.env' \\"
echo "  main.py src/ requirements.txt config.yaml"
echo ""
echo "# 上传到服务器（需要输入服务器密码或使用网页上传）"
echo "scp crypto-bot.tar.gz root@119.28.43.237:/opt/crypto-monitor-bot/"
echo ""
echo "上传完成后，在服务器执行:"
echo "cd /opt/crypto-monitor-bot && tar -xzf crypto-bot.tar.gz"
echo ""
read -p "代码已上传？按回车继续，或 Ctrl+C 退出..."

# 5. 解压代码（如果已上传）
if [ -f crypto-bot.tar.gz ]; then
    echo "📦 解压代码..."
    tar -xzf crypto-bot.tar.gz
    rm crypto-bot.tar.gz
else
    echo "❌ 未找到代码包，请先上传代码"
    exit 1
fi

# 6. 安装 Python 依赖
echo "🐍 安装 Python 依赖..."
python3.9 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 7. 创建配置
echo "⚙️ 创建配置..."
cat > .env << 'ENV_EOF'
TELEGRAM_BOT_TOKEN=8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68
TELEGRAM_CHAT_ID=6954384980
POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=P@ssw0rd2024!Crypto#DB
POSTGRES_DB=crypto_monitor
DATABASE_URL=postgresql://cryptobot:P@ssw0rd2024!Crypto#DB@localhost:5432/crypto_monitor
REDIS_PASSWORD=R3dis$Secure#2024Pass!
REDIS_URL=redis://:R3dis$Secure#2024Pass!@localhost:6379/0
LOG_LEVEL=INFO
ENV_EOF
chmod 600 .env

# 8. 配置自启动
echo "🔧 配置自启动..."
cat > /etc/supervisor/conf.d/crypto-monitor-bot.conf << 'SUPER_EOF'
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
SUPER_EOF

supervisorctl reread && supervisorctl update
supervisorctl start crypto-monitor-bot

sleep 3

echo ""
echo "✅ 部署完成！"
supervisorctl status crypto-monitor-bot
echo ""
echo "查看日志: tail -f /var/log/crypto-monitor-bot.log"
