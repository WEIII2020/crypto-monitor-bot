# 🚀 最终部署步骤 - 复制粘贴即可

**你的完整配置信息：**
```
✅ 服务器IP: 119.28.43.237
✅ Telegram Bot Token: 8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68
✅ Telegram Chat ID: 6954384980
✅ PostgreSQL密码: P@ssw0rd2024!Crypto#DB
✅ Redis密码: R3dis$Secure#2024Pass!
```

---

## 📋 部署流程（3个命令）

### 步骤1️⃣：在本地上传代码（2分钟）

**在你的 Mac 终端执行**：

```bash
cd "/Users/szld2403203/Library/Mobile Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot"

# 运行上传脚本
bash upload_to_server.sh
```

这个脚本会：
- ✅ 打包项目代码
- ✅ 上传到服务器
- ✅ 上传部署脚本

---

### 步骤2️⃣：连接到服务器（10秒）

```bash
ssh root@119.28.43.237
```

输入服务器密码后，你会进入服务器终端。

---

### 步骤3️⃣：运行自动部署（10分钟）

**在服务器上执行**：

```bash
# 如果上传了 auto_deploy.sh（推荐）
bash /root/auto_deploy.sh
```

**或者使用完整部署脚本**：

```bash
bash /root/deploy_tencent_cloud.sh
```

### 按照提示输入：

当脚本询问时，输入以下信息：

| 提示 | 输入内容 |
|------|---------|
| 是否继续？ | `y` |
| PostgreSQL 用户名 | 直接回车（默认 cryptobot） |
| PostgreSQL 密码 | `P@ssw0rd2024!Crypto#DB` |
| 数据库名 | 直接回车（默认 crypto_monitor） |
| Redis 密码 | `R3dis$Secure#2024Pass!` |
| 获取代码方式 | `2`（已手动上传） |
| Telegram Bot Token | `8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68` |
| Telegram Chat ID | `6954384980` |
| 配置 Binance API | `n` |
| 测试是否成功 | `y`（如果看到 "Bot is running!"） |
| 配置防火墙 | `y` |
| 配置自动备份 | `y` |

---

## ⚡ 或者：一键快速部署（完全自动）

如果想完全自动化，**直接在服务器上运行这个命令**（已预配置所有信息）：

```bash
cd /root

# 下载并解压代码
tar -xzf crypto-bot.tar.gz -C /opt/ && mv /opt/crypto-monitor-bot /opt/crypto-monitor-bot-backup 2>/dev/null || true
mkdir -p /opt/crypto-monitor-bot
tar -xzf crypto-bot.tar.gz -C /opt/crypto-monitor-bot/

# 一键部署
cat > /tmp/quick_deploy.sh << 'QUICK_DEPLOY_EOF'
#!/bin/bash
set -e

echo "🚀 开始自动部署..."

# 安装依赖
apt update && apt install -y python3.9 python3.9-venv python3-pip postgresql postgresql-contrib redis-server supervisor

# 配置 PostgreSQL
sudo -u postgres psql << 'PSQL_EOF'
DROP DATABASE IF EXISTS crypto_monitor;
DROP USER IF EXISTS cryptobot;
CREATE USER cryptobot WITH PASSWORD 'P@ssw0rd2024!Crypto#DB';
CREATE DATABASE crypto_monitor OWNER cryptobot;
GRANT ALL PRIVILEGES ON DATABASE crypto_monitor TO cryptobot;
\q
PSQL_EOF

echo "host all all 127.0.0.1/32 md5" >> /etc/postgresql/*/main/pg_hba.conf
systemctl restart postgresql

# 配置 Redis
cp /etc/redis/redis.conf /etc/redis/redis.conf.bak
sed -i 's/# requirepass.*/requirepass R3dis$Secure#2024Pass!/' /etc/redis/redis.conf
sed -i 's/^bind .*/bind 127.0.0.1/' /etc/redis/redis.conf
systemctl restart redis

# 安装 Python 依赖
cd /opt/crypto-monitor-bot
python3.9 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 创建配置
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

# 配置 Supervisor
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

supervisorctl reread
supervisorctl update
supervisorctl start crypto-monitor-bot

echo ""
echo "✅ 部署完成！"
echo "查看日志: tail -f /var/log/crypto-monitor-bot.log"
echo "查看状态: supervisorctl status"
QUICK_DEPLOY_EOF

bash /tmp/quick_deploy.sh
```

---

## ✅ 验证部署成功

### 1. 查看服务状态

```bash
supervisorctl status crypto-monitor-bot
```

**期望输出**：
```
crypto-monitor-bot   RUNNING   pid 1234, uptime 0:01:00
```

### 2. 查看实时日志

```bash
tail -f /var/log/crypto-monitor-bot.log
```

**期望看到**：
```
🚀 Starting Crypto Monitor Bot...
✅ Database connections established
✅ Selected 50 symbols
✅ Bot is running!
```

按 `Ctrl+C` 退出日志查看。

### 3. 检查 Telegram 消息

打开你的 Telegram，应该已经收到测试消息：
```
🎉 部署成功！

✅ 服务器: 119.28.43.237
✅ 监控已启动
✅ 开始监控 50+ 加密货币

等待价格波动时会收到告警 📊
```

---

## 🎯 常用管理命令

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

# 搜索告警
grep "🚨" /var/log/crypto-monitor-bot.log
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

# 常用 SQL 命令
\dt                    # 查看所有表
\d+ prices            # 查看 prices 表结构
SELECT * FROM prices ORDER BY timestamp DESC LIMIT 10;  # 查看最新价格
SELECT * FROM alerts ORDER BY created_at DESC LIMIT 10; # 查看最新告警
\q                    # 退出
```

---

## 🔧 故障排查

### 如果服务未启动

```bash
# 查看详细日志
tail -n 100 /var/log/crypto-monitor-bot.log

# 手动运行查看错误
cd /opt/crypto-monitor-bot
source venv/bin/activate
python main.py
```

### 如果数据库连接失败

```bash
# 测试 PostgreSQL
systemctl status postgresql
psql -U cryptobot -d crypto_monitor -h localhost

# 测试 Redis
systemctl status redis
redis-cli -a 'R3dis$Secure#2024Pass!' ping
```

### 如果无法收到 Telegram 消息

```bash
# 测试网络
curl https://api.telegram.org

# 测试 Bot
curl https://api.telegram.org/bot8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68/getMe

# 手动发送测试消息
cd /opt/crypto-monitor-bot
source venv/bin/activate

python3 << 'TEST_EOF'
import asyncio
from dotenv import load_dotenv
from src.notifiers.telegram_notifier import TelegramNotifier

load_dotenv()

async def test():
    notifier = TelegramNotifier()
    await notifier.send_message("测试消息")

asyncio.run(test())
TEST_EOF
```

---

## 🎨 自定义配置（可选）

### 修改监控币种数量

```bash
nano /opt/crypto-monitor-bot/config.yaml

# 修改
symbols:
  max_count: 100  # 从 50 改为 100

# 重启服务
supervisorctl restart crypto-monitor-bot
```

### 修改告警阈值

```bash
nano /opt/crypto-monitor-bot/config.yaml

# 修改
volatility:
  warning_threshold: 5.0   # 从 10% 改为 5%
  critical_threshold: 15.0 # 从 20% 改为 15%

# 重启服务
supervisorctl restart crypto-monitor-bot
```

---

## 📊 部署信息汇总

**请妥善保管以下信息**：

```
════════════════════════════════════════
  部署信息 - 请保存到安全的地方
════════════════════════════════════════

服务器:
  IP: 119.28.43.237
  SSH: ssh root@119.28.43.237
  
项目:
  目录: /opt/crypto-monitor-bot
  日志: /var/log/crypto-monitor-bot.log
  配置: /opt/crypto-monitor-bot/.env
  
PostgreSQL:
  主机: localhost:5432
  数据库: crypto_monitor
  用户: cryptobot
  密码: P@ssw0rd2024!Crypto#DB
  
Redis:
  主机: localhost:6379
  密码: R3dis$Secure#2024Pass!
  
Telegram:
  Bot Token: 8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68
  Chat ID: 6954384980
  机器人: @lucascryptomonitorbot

常用命令:
  状态: supervisorctl status
  日志: tail -f /var/log/crypto-monitor-bot.log
  重启: supervisorctl restart crypto-monitor-bot

════════════════════════════════════════
```

---

## 🎉 完成！

现在你可以：

1. **等待告警** - 当价格波动超过阈值时，会在 Telegram 收到通知
2. **监控日志** - 实时查看机器人的运行状态
3. **调整配置** - 根据需求修改监控参数

**祝你使用愉快！** 🚀

如有问题，随时查看 [TENCENT_CLOUD_DEPLOYMENT.md](TENCENT_CLOUD_DEPLOYMENT.md) 获取详细帮助。
