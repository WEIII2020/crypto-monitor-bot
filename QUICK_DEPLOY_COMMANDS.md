# ⚡ 快速部署命令清单

**直接复制粘贴执行**

---

## 📋 准备工作（在本地完成）

### 1. 获取 Telegram Chat ID

在浏览器打开以下链接（先确保给机器人发送了 /start）：
```
https://api.telegram.org/bot8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68/getUpdates
```

在页面中搜索 `"id":` 后面的数字，记录下来：
```
我的 Chat ID: _______________（例如：1234567890）
```

### 2. 生成密码（可选）

```bash
# 在本地 Mac/Linux 终端运行
echo "PostgreSQL密码: $(openssl rand -base64 16)"
echo "Redis密码: $(openssl rand -base64 16)"
```

记录下来：
```
PostgreSQL密码: _______________
Redis密码: _______________
```

---

## 🚀 开始部署（在服务器执行）

### Step 1: 连接到服务器

```bash
ssh root@119.28.43.237
```

### Step 2: 下载或创建部署脚本

**方法A：如果能访问GitHub**
```bash
cd /root
wget https://raw.githubusercontent.com/your-repo/crypto-monitor-bot/main/deploy_tencent_cloud.sh
chmod +x deploy_tencent_cloud.sh
```

**方法B：手动创建（推荐）**

复制整个下面的命令块（包括 EOF）：

```bash
cat > /root/deploy_tencent_cloud.sh << 'EOF'
# ⚠️ 这里需要粘贴 deploy_tencent_cloud.sh 的完整内容
# 由于内容太长，建议使用以下简化版脚本
EOF

chmod +x /root/deploy_tencent_cloud.sh
```

### Step 3: 运行部署脚本

```bash
bash /root/deploy_tencent_cloud.sh
```

---

## 🎯 简化版手动部署（如果自动脚本失败）

### 1. 更新系统并安装依赖

```bash
# 一次性安装所有依赖
apt update && apt upgrade -y && \
apt install -y python3.9 python3.9-venv python3-pip \
               postgresql postgresql-contrib \
               redis-server git supervisor \
               htop curl wget vim
```

### 2. 配置 PostgreSQL

```bash
# 创建数据库和用户（修改密码）
sudo -u postgres psql << 'PSQL_COMMANDS'
CREATE USER cryptobot WITH PASSWORD 'YOUR_POSTGRES_PASSWORD_HERE';
CREATE DATABASE crypto_monitor OWNER cryptobot;
GRANT ALL PRIVILEGES ON DATABASE crypto_monitor TO cryptobot;
\q
PSQL_COMMANDS

# 配置访问权限
echo "host    all             all             127.0.0.1/32            md5" >> /etc/postgresql/*/main/pg_hba.conf
systemctl restart postgresql
systemctl enable postgresql
```

### 3. 配置 Redis

```bash
# 设置 Redis 密码（修改密码）
sed -i 's/# requirepass foobared/requirepass YOUR_REDIS_PASSWORD_HERE/' /etc/redis/redis.conf

# 重启 Redis
systemctl restart redis
systemctl enable redis
```

### 4. 部署项目

```bash
# 创建项目目录
mkdir -p /opt/crypto-monitor-bot
cd /opt/crypto-monitor-bot

# 从本地上传代码（在本地电脑运行）
# scp -r /Users/szld2403203/Library/Mobile\ Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot/* root@119.28.43.237:/opt/crypto-monitor-bot/

# 或克隆 Git 仓库（如果有）
# git clone https://github.com/your-username/crypto-monitor-bot.git .

# 创建虚拟环境
python3.9 -m venv venv

# 安装依赖
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. 配置环境变量

```bash
# 创建 .env 文件
cat > /opt/crypto-monitor-bot/.env << 'ENV_FILE'
# Telegram Bot
TELEGRAM_BOT_TOKEN=8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68
TELEGRAM_CHAT_ID=YOUR_CHAT_ID_HERE

# Database
POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=YOUR_POSTGRES_PASSWORD_HERE
POSTGRES_DB=crypto_monitor
DATABASE_URL=postgresql://cryptobot:YOUR_POSTGRES_PASSWORD_HERE@localhost:5432/crypto_monitor

# Redis
REDIS_PASSWORD=YOUR_REDIS_PASSWORD_HERE
REDIS_URL=redis://:YOUR_REDIS_PASSWORD_HERE@localhost:6379/0

# Logging
LOG_LEVEL=INFO
ENV_FILE

# 修改文件权限
chmod 600 /opt/crypto-monitor-bot/.env
```

**⚠️ 记得修改以下内容**：
- `YOUR_CHAT_ID_HERE` → 你的 Chat ID 数字
- `YOUR_POSTGRES_PASSWORD_HERE` → 你设置的 PostgreSQL 密码（两处）
- `YOUR_REDIS_PASSWORD_HERE` → 你设置的 Redis 密码（两处）

### 6. 测试运行

```bash
cd /opt/crypto-monitor-bot
source venv/bin/activate

# 测试运行 15 秒
timeout 15 python main.py

# 应该看到:
# ✅ Database connections established
# ✅ Selected 50 symbols
# ✅ Bot is running!
```

### 7. 配置开机自启动

```bash
# 创建 Supervisor 配置
cat > /etc/supervisor/conf.d/crypto-monitor-bot.conf << 'SUPERVISOR_CONFIG'
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
SUPERVISOR_CONFIG

# 启动服务
supervisorctl reread
supervisorctl update
supervisorctl start crypto-monitor-bot

# 查看状态
supervisorctl status
```

### 8. 配置防火墙（可选但推荐）

```bash
# 配置 UFW 防火墙
apt install -y ufw
ufw allow 22/tcp
ufw --force enable
ufw status
```

---

## ✅ 验证部署

### 查看运行状态

```bash
supervisorctl status crypto-monitor-bot
```

期望输出：`crypto-monitor-bot   RUNNING   pid 1234, uptime 0:01:00`

### 查看日志

```bash
tail -f /var/log/crypto-monitor-bot.log
```

### 发送测试消息

```bash
cd /opt/crypto-monitor-bot
source venv/bin/activate

# 创建测试脚本
cat > test_telegram.py << 'TEST_SCRIPT'
import os
import asyncio
from dotenv import load_dotenv
from src.notifiers.telegram_notifier import TelegramNotifier

load_dotenv()

async def test():
    print("正在发送测试消息...")
    notifier = TelegramNotifier()
    await notifier.send_message("🎉 部署成功！监控机器人已启动。")
    print("✅ 测试消息已发送，请检查 Telegram")

asyncio.run(test())
TEST_SCRIPT

# 运行测试
python test_telegram.py
```

---

## 📊 常用命令

### 服务管理

```bash
# 查看状态
supervisorctl status

# 重启服务
supervisorctl restart crypto-monitor-bot

# 停止服务
supervisorctl stop crypto-monitor-bot

# 启动服务
supervisorctl start crypto-monitor-bot
```

### 日志查看

```bash
# 实时日志
tail -f /var/log/crypto-monitor-bot.log

# 最近 100 行
tail -n 100 /var/log/crypto-monitor-bot.log

# 搜索错误
grep ERROR /var/log/crypto-monitor-bot.log
```

### 系统监控

```bash
# 查看资源使用
htop

# 查看内存
free -h

# 查看磁盘
df -h

# 查看进程
ps aux | grep python
```

### 数据库操作

```bash
# 连接 PostgreSQL
psql -U cryptobot -d crypto_monitor

# 查看表
\dt

# 查看最近价格
SELECT * FROM prices ORDER BY timestamp DESC LIMIT 10;

# 查看告警
SELECT * FROM alerts ORDER BY created_at DESC LIMIT 10;

# 退出
\q
```

---

## 🔧 故障排查

### 如果服务无法启动

```bash
# 1. 查看详细日志
tail -n 100 /var/log/crypto-monitor-bot.log

# 2. 手动运行查看错误
cd /opt/crypto-monitor-bot
source venv/bin/activate
python main.py

# 3. 检查配置文件
cat .env

# 4. 测试数据库连接
psql -U cryptobot -d crypto_monitor -h localhost

# 5. 测试 Redis 连接
redis-cli -a 你的Redis密码 ping
```

### 如果无法收到 Telegram 消息

```bash
# 1. 测试网络
curl https://api.telegram.org

# 2. 测试 Bot API
curl https://api.telegram.org/bot8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68/getMe

# 3. 查看 .env 配置
grep TELEGRAM /opt/crypto-monitor-bot/.env

# 4. 确认已给机器人发送 /start
```

---

## 🎉 部署完成检查清单

- [ ] 服务状态为 RUNNING
- [ ] 日志显示 "Bot is running!"
- [ ] 可以连接到 PostgreSQL
- [ ] Redis 正常运行
- [ ] 收到 Telegram 测试消息
- [ ] 防火墙已配置
- [ ] 已记录所有密码和配置

---

## 📝 重要信息记录

```
部署完成时间: _______________

服务器信息:
  IP: 119.28.43.237
  SSH: ssh root@119.28.43.237

项目信息:
  目录: /opt/crypto-monitor-bot
  日志: /var/log/crypto-monitor-bot.log

数据库:
  PostgreSQL: localhost:5432/crypto_monitor
  用户: cryptobot
  密码: _______________

  Redis: localhost:6379
  密码: _______________

Telegram:
  Token: 8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68
  Chat ID: _______________
```

---

**祝你部署成功！** 🚀

如有问题，查看 [MY_DEPLOYMENT_STEPS.md](MY_DEPLOYMENT_STEPS.md) 获取详细指导。
