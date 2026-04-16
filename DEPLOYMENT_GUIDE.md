# 🚀 腾讯云部署指南

完整的云端部署教程，实现24小时稳定运行。

---

## 📋 部署前准备清单

### 1. 服务器信息
- [ ] 服务器IP地址: `_______________`
- [ ] SSH端口: `_____` (默认22)
- [ ] 操作系统: Ubuntu 20.04/22.04 (推荐) / CentOS 7/8
- [ ] 配置: 2核2GB+ (推荐 2核4GB)
- [ ] SSH登录方式: 密码 / 密钥

### 2. 必需的配置信息
- [ ] Telegram Bot Token
- [ ] Telegram Chat ID
- [ ] 服务器防火墙规则 (开放必要端口)

---

## 🔧 快速部署（一键脚本）

### 方式1: 自动化部署脚本

在**本地**运行以下命令，自动完成所有部署步骤：

```bash
# 1. 进入项目目录
cd /Users/szld2403203/Library/Mobile\ Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot

# 2. 运行部署脚本（需要输入服务器IP和密码）
./deploy_to_cloud.sh
```

脚本会自动完成：
- ✅ 环境依赖安装 (Python, Redis, PostgreSQL)
- ✅ 代码上传
- ✅ 配置文件设置
- ✅ systemd服务配置
- ✅ 自动启动设置

---

## 📝 手动部署（完整步骤）

如果自动脚本失败，按以下步骤手动部署。

### Step 1: 连接服务器

```bash
# 使用密码登录
ssh root@YOUR_SERVER_IP

# 或使用密钥登录
ssh -i /path/to/key.pem root@YOUR_SERVER_IP
```

### Step 2: 安装系统依赖

#### Ubuntu/Debian:

```bash
# 更新系统
apt update && apt upgrade -y

# 安装基础工具
apt install -y git curl wget vim unzip

# 安装Python 3.9+
apt install -y python3 python3-pip python3-venv

# 安装Redis
apt install -y redis-server
systemctl start redis-server
systemctl enable redis-server

# 安装PostgreSQL
apt install -y postgresql postgresql-contrib
systemctl start postgresql
systemctl enable postgresql
```

#### CentOS/RedHat:

```bash
# 更新系统
yum update -y

# 安装基础工具
yum install -y git curl wget vim unzip

# 安装Python 3.9
yum install -y python39 python39-pip

# 安装Redis
yum install -y redis
systemctl start redis
systemctl enable redis

# 安装PostgreSQL
yum install -y postgresql-server postgresql-contrib
postgresql-setup initdb
systemctl start postgresql
systemctl enable postgresql
```

### Step 3: 配置PostgreSQL

```bash
# 切换到postgres用户
sudo -u postgres psql

# 在PostgreSQL控制台中执行：
CREATE USER cryptobot WITH PASSWORD 'your_secure_password_here';
CREATE DATABASE crypto_monitor OWNER cryptobot;
GRANT ALL PRIVILEGES ON DATABASE crypto_monitor TO cryptobot;
\q

# 配置PostgreSQL允许本地连接
# 编辑 /etc/postgresql/*/main/pg_hba.conf (Ubuntu)
# 或 /var/lib/pgsql/data/pg_hba.conf (CentOS)
# 添加以下行：
local   all             cryptobot                               md5
host    all             cryptobot       127.0.0.1/32            md5

# 重启PostgreSQL
systemctl restart postgresql
```

### Step 4: 上传代码到服务器

#### 方式A: 使用Git (推荐)

```bash
# 在服务器上
cd /opt
git clone <your-repo-url> crypto-monitor-bot
cd crypto-monitor-bot
```

#### 方式B: 使用SCP从本地上传

```bash
# 在本地Mac上运行
cd /Users/szld2403203/Library/Mobile\ Documents/com~apple~CloudDocs/Cursor
tar -czf crypto-monitor-bot.tar.gz crypto-monitor-bot --exclude=crypto-monitor-bot/venv --exclude=crypto-monitor-bot/__pycache__ --exclude=crypto-monitor-bot/logs

scp crypto-monitor-bot.tar.gz root@YOUR_SERVER_IP:/opt/

# 在服务器上解压
ssh root@YOUR_SERVER_IP
cd /opt
tar -xzf crypto-monitor-bot.tar.gz
cd crypto-monitor-bot
```

### Step 5: 配置环境

```bash
# 创建Python虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
vim .env  # 或使用 nano .env
```

编辑 `.env` 文件：

```bash
# Telegram配置
TELEGRAM_BOT_TOKEN=你的Bot_Token
TELEGRAM_CHAT_ID=你的Chat_ID

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# PostgreSQL配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=crypto_monitor
POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=your_secure_password_here

# 监控配置
MAX_SYMBOLS=50
CHECK_INTERVAL=30
```

### Step 6: 测试运行

```bash
# 激活虚拟环境
source venv/bin/activate

# 测试运行（前台）
python main.py

# 如果看到以下信息说明成功：
# ✅ Database connections established
# ✅ Selected 47 symbols
# ✅ Subscribed to 47 symbols
# ✅ Bot is running!

# 按 Ctrl+C 停止测试
```

### Step 7: 配置systemd服务（推荐）

创建systemd服务文件：

```bash
sudo vim /etc/systemd/system/crypto-monitor.service
```

添加以下内容：

```ini
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
```

启动服务：

```bash
# 重载systemd配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start crypto-monitor

# 设置开机自启
sudo systemctl enable crypto-monitor

# 查看服务状态
sudo systemctl status crypto-monitor

# 查看实时日志
sudo journalctl -u crypto-monitor -f
```

### Step 8: 配置防火墙（可选）

```bash
# Ubuntu (ufw)
ufw allow 22/tcp  # SSH
ufw enable

# CentOS (firewalld)
firewall-cmd --permanent --add-service=ssh
firewall-cmd --reload
```

---

## 🔍 验证部署

### 1. 检查服务状态

```bash
# 查看服务状态
systemctl status crypto-monitor

# 应该看到：
# Active: active (running)
```

### 2. 检查日志

```bash
# 查看应用日志
tail -f /opt/crypto-monitor-bot/logs/crypto_monitor_$(date +%Y-%m-%d).log

# 查看systemd日志
journalctl -u crypto-monitor -n 50
```

### 3. 检查数据库

```bash
# Redis
redis-cli ping
# 应该返回: PONG

# PostgreSQL
sudo -u postgres psql -d crypto_monitor -c "SELECT COUNT(*) FROM price_data;"
# 应该看到数据行数
```

### 4. 测试Telegram通知

```bash
# 在服务器上运行测试脚本
cd /opt/crypto-monitor-bot
source venv/bin/activate
python test_telegram.py
```

---

## 🛠️ 日常管理命令

### 服务控制

```bash
# 启动
sudo systemctl start crypto-monitor

# 停止
sudo systemctl stop crypto-monitor

# 重启
sudo systemctl restart crypto-monitor

# 查看状态
sudo systemctl status crypto-monitor

# 查看日志
sudo journalctl -u crypto-monitor -f
```

### 日志管理

```bash
# 查看今天的日志
tail -f /opt/crypto-monitor-bot/logs/crypto_monitor_$(date +%Y-%m-%d).log

# 查看错误日志
grep "ERROR" /opt/crypto-monitor-bot/logs/crypto_monitor_$(date +%Y-%m-%d).log

# 清理旧日志（保留30天）
find /opt/crypto-monitor-bot/logs -name "*.log.zip" -mtime +30 -delete
```

### 更新代码

```bash
# 停止服务
sudo systemctl stop crypto-monitor

# 更新代码
cd /opt/crypto-monitor-bot
git pull origin main

# 或从本地上传（在本地执行）
scp -r src/ root@YOUR_SERVER_IP:/opt/crypto-monitor-bot/

# 重启服务
sudo systemctl start crypto-monitor
```

---

## 🔧 性能监控

### 创建监控脚本

```bash
cat > /opt/crypto-monitor-bot/monitor.sh << 'EOF'
#!/bin/bash
echo "=== Crypto Monitor Bot Status ==="
echo ""
echo "Service Status:"
systemctl is-active crypto-monitor && echo "  ✅ Running" || echo "  ❌ Stopped"
echo ""
echo "Resources:"
ps aux | grep "main.py" | grep -v grep | awk '{print "  CPU: "$3"% | MEM: "$4"% | PID: "$2}'
echo ""
echo "Data Processing:"
tail -1 /opt/crypto-monitor-bot/logs/crypto_monitor_$(date +%Y-%m-%d).log | grep "Performance Report" || echo "  No recent stats"
echo ""
echo "Database:"
redis-cli ping > /dev/null 2>&1 && echo "  ✅ Redis: OK" || echo "  ❌ Redis: Failed"
pg_isready -h localhost > /dev/null 2>&1 && echo "  ✅ PostgreSQL: OK" || echo "  ❌ PostgreSQL: Failed"
EOF

chmod +x /opt/crypto-monitor-bot/monitor.sh
```

运行监控：

```bash
/opt/crypto-monitor-bot/monitor.sh
```

### 设置定时监控（可选）

```bash
# 添加到crontab，每小时检查一次
crontab -e

# 添加以下行：
0 * * * * /opt/crypto-monitor-bot/monitor.sh >> /opt/crypto-monitor-bot/logs/monitor.log 2>&1
```

---

## 🚨 故障排查

### 问题1: 服务启动失败

```bash
# 查看详细错误
sudo journalctl -u crypto-monitor -n 50 --no-pager

# 检查配置文件
cat /opt/crypto-monitor-bot/.env

# 手动运行看错误
cd /opt/crypto-monitor-bot
source venv/bin/activate
python main.py
```

### 问题2: Redis连接失败

```bash
# 检查Redis状态
systemctl status redis-server  # Ubuntu
# 或
systemctl status redis  # CentOS

# 测试连接
redis-cli ping

# 重启Redis
sudo systemctl restart redis-server
```

### 问题3: PostgreSQL连接失败

```bash
# 检查PostgreSQL状态
systemctl status postgresql

# 测试连接
psql -h localhost -U cryptobot -d crypto_monitor

# 查看日志
sudo tail -f /var/log/postgresql/postgresql-*.log
```

### 问题4: 没有收到Telegram通知

```bash
# 测试网络连接
curl -I https://api.telegram.org

# 测试Bot Token
curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe

# 检查配置
grep TELEGRAM /opt/crypto-monitor-bot/.env
```

### 问题5: 内存占用过高

```bash
# 检查内存使用
free -h
ps aux --sort=-%mem | head -10

# 减少监控币种数量
vim /opt/crypto-monitor-bot/config.yaml
# 修改 max_count: 30  # 从50改为30

# 重启服务
sudo systemctl restart crypto-monitor
```

---

## 🔐 安全建议

### 1. 更改SSH端口

```bash
# 编辑SSH配置
vim /etc/ssh/sshd_config

# 修改端口
Port 2222  # 使用非标准端口

# 重启SSH
systemctl restart sshd
```

### 2. 配置防火墙

```bash
# 只允许SSH和必要端口
ufw default deny incoming
ufw default allow outgoing
ufw allow 2222/tcp  # 新SSH端口
ufw enable
```

### 3. 定期备份

```bash
# 创建备份脚本
cat > /opt/backup_crypto_bot.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups"
mkdir -p $BACKUP_DIR
DATE=$(date +%Y%m%d_%H%M%S)

# 备份数据库
PGPASSWORD=your_password pg_dump -h localhost -U cryptobot crypto_monitor > $BACKUP_DIR/db_$DATE.sql

# 备份配置
cp /opt/crypto-monitor-bot/.env $BACKUP_DIR/env_$DATE

# 清理旧备份（保留7天）
find $BACKUP_DIR -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /opt/backup_crypto_bot.sh

# 添加到crontab（每天凌晨3点备份）
# 0 3 * * * /opt/backup_crypto_bot.sh
```

---

## 📊 性能优化建议

### 1. 针对低配置服务器（1核2GB）

```yaml
# config.yaml
symbols:
  max_count: 30  # 减少监控币种

volatility:
  check_interval: 60  # 增加检查间隔到60秒
```

### 2. 针对标准配置（2核4GB）

```yaml
# config.yaml
symbols:
  max_count: 50  # 默认配置

volatility:
  check_interval: 30  # 30秒间隔
```

### 3. 针对高配置（4核8GB）

```yaml
# config.yaml
symbols:
  max_count: 100  # 监控更多币种

volatility:
  check_interval: 15  # 更快的检测
```

---

## 📞 支持

如果遇到问题：

1. 查看日志: `journalctl -u crypto-monitor -n 100`
2. 运行监控脚本: `/opt/crypto-monitor-bot/monitor.sh`
3. 查看TROUBLESHOOTING.md
4. 提交Issue到GitHub

---

**部署完成后，你的Bot将：**
- ✅ 24小时稳定运行
- ✅ 自动重启（服务崩溃时）
- ✅ 开机自启动
- ✅ 日志自动管理
- ✅ 性能监控

**预计部署时间:** 15-30分钟

**最后更新:** 2026-04-15
