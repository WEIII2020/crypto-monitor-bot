# 腾讯云部署指南

本指南提供两种腾讯云部署方案，适合不同需求和预算。

---

## 📋 部署前准备

### 1. 确认已购买的服务
- [ ] 腾讯云账号（已完成）
- [ ] 实名认证
- [ ] 充值账户余额（建议 ¥100+）

### 2. 获取必要的API密钥

#### Telegram Bot Token
```bash
# 1. 在Telegram搜索 @BotFather
# 2. 发送 /newbot 创建新机器人
# 3. 获取 Bot Token（格式：123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11）
# 4. 发送 /start 给你的机器人

# 获取 Chat ID
# 1. 在Telegram搜索 @userinfobot
# 2. 发送 /start
# 3. 获取你的 Chat ID（格式：123456789）
```

---

## 🎯 方案一：轻量应用服务器（推荐新手）

**适合场景**：个人使用、测试环境、小规模监控
**预计成本**：¥50-100/月

### Step 1: 购买轻量应用服务器

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
2. 搜索并进入「轻量应用服务器」
3. 点击「新建」，选择配置：
   - **地域**：选择离你近的（如北京、上海、广州）
   - **镜像**：Docker 基础镜像 或 Ubuntu 20.04
   - **套餐**：
     - CPU：2核
     - 内存：2GB（最低配置）
     - 带宽：3Mbps
     - 流量包：300GB/月
   - **价格**：约 ¥50-80/月

4. 购买完成后，记录：
   - 公网IP地址
   - 实例ID

### Step 2: 配置服务器安全

1. 在轻量应用服务器控制台，点击「防火墙」
2. 添加以下规则（**重要：只开放必要端口**）：
   ```
   应用类型    协议    端口    源地址        操作
   SSH         TCP    22      0.0.0.0/0    允许
   HTTP        TCP    80      0.0.0.0/0    允许
   HTTPS       TCP    443     0.0.0.0/0    允许
   自定义      TCP    6379    127.0.0.1    拒绝  (Redis - 仅本地访问)
   自定义      TCP    5432    127.0.0.1    拒绝  (PostgreSQL - 仅本地访问)
   ```

### Step 3: 连接到服务器

#### 方法1：使用腾讯云网页终端（推荐）
1. 在控制台点击实例名称
2. 点击「登录」按钮
3. 选择「浏览器 VNC 登录」

#### 方法2：使用SSH（推荐专业用户）
```bash
# Mac/Linux
ssh root@你的服务器IP

# Windows：使用 PuTTY 或 Windows Terminal
```

### Step 4: 安装依赖环境

```bash
# 1. 更新系统
apt update && apt upgrade -y

# 2. 安装 Python 3.9+
apt install -y python3.9 python3.9-venv python3-pip

# 3. 安装 PostgreSQL
apt install -y postgresql postgresql-contrib

# 4. 安装 Redis
apt install -y redis-server

# 5. 安装 Git
apt install -y git

# 6. 安装 supervisor（进程管理）
apt install -y supervisor
```

### Step 5: 配置数据库

#### PostgreSQL 配置
```bash
# 切换到 postgres 用户
sudo -u postgres psql

# 在 PostgreSQL 命令行中执行：
CREATE USER cryptobot WITH PASSWORD 'your_strong_password_here';
CREATE DATABASE crypto_monitor OWNER cryptobot;
GRANT ALL PRIVILEGES ON DATABASE crypto_monitor TO cryptobot;
\q  -- 退出

# 设置 PostgreSQL 允许本地连接
echo "host    all             all             127.0.0.1/32            md5" >> /etc/postgresql/12/main/pg_hba.conf
systemctl restart postgresql
```

#### Redis 配置
```bash
# 编辑 Redis 配置
nano /etc/redis/redis.conf

# 修改以下内容：
# 1. 找到 "bind 127.0.0.1" 行，确保只监听本地
# 2. 找到 "# requirepass foobared"，取消注释并设置密码：
requirepass your_redis_password_here

# 保存并退出 (Ctrl+X, Y, Enter)

# 重启 Redis
systemctl restart redis
systemctl enable redis
```

### Step 6: 部署项目

```bash
# 1. 创建项目目录
mkdir -p /opt/crypto-monitor-bot
cd /opt/crypto-monitor-bot

# 2. 克隆代码（如果你已经上传到GitHub/Gitee）
git clone https://github.com/your-username/crypto-monitor-bot.git .

# 或者使用 scp 上传本地代码：
# scp -r /path/to/local/crypto-monitor-bot root@服务器IP:/opt/

# 3. 创建虚拟环境
python3.9 -m venv venv
source venv/bin/activate

# 4. 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 5. 创建配置文件
cp .env.example .env
nano .env
```

**编辑 .env 文件**：
```bash
# Telegram Bot（必填）
TELEGRAM_BOT_TOKEN=你的Telegram_Bot_Token
TELEGRAM_CHAT_ID=你的Chat_ID

# Database（必填）
POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=你设置的PostgreSQL密码
POSTGRES_DB=crypto_monitor
DATABASE_URL=postgresql://cryptobot:你设置的PostgreSQL密码@localhost:5432/crypto_monitor

# Redis（必填）
REDIS_PASSWORD=你设置的Redis密码
REDIS_URL=redis://:你设置的Redis密码@localhost:6379/0

# Exchange APIs（可选，使用公开数据不需要）
BINANCE_API_KEY=
BINANCE_API_SECRET=

# Logging
LOG_LEVEL=INFO
```

### Step 7: 测试运行

```bash
# 激活虚拟环境
cd /opt/crypto-monitor-bot
source venv/bin/activate

# 测试运行
python main.py

# 应该看到类似输出：
# 🚀 Starting Crypto Monitor Bot...
# ✅ Database connections established
# ✅ Selected 50 symbols
# ✅ Subscribed to 50 symbols
# ✅ Bot is running!

# 按 Ctrl+C 停止测试
```

### Step 8: 配置开机自启动（使用 Supervisor）

```bash
# 创建 supervisor 配置
nano /etc/supervisor/conf.d/crypto-monitor-bot.conf
```

**配置内容**：
```ini
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
```

```bash
# 重载 supervisor 配置
supervisorctl reread
supervisorctl update
supervisorctl start crypto-monitor-bot

# 查看运行状态
supervisorctl status crypto-monitor-bot

# 查看日志
tail -f /var/log/crypto-monitor-bot.log
```

### Step 9: 常用管理命令

```bash
# 查看运行状态
supervisorctl status

# 停止服务
supervisorctl stop crypto-monitor-bot

# 启动服务
supervisorctl start crypto-monitor-bot

# 重启服务
supervisorctl restart crypto-monitor-bot

# 查看实时日志
tail -f /var/log/crypto-monitor-bot.log

# 查看系统资源使用
htop
```

---

## 🏢 方案二：云服务器 + 云数据库（推荐生产环境）

**适合场景**：生产环境、高可用、数据库备份
**预计成本**：¥200-500/月

### Step 1: 购买云服务器 CVM

1. 进入 [CVM 控制台](https://console.cloud.tencent.com/cvm)
2. 点击「新建」，配置：
   - **计费模式**：按量计费（灵活）或包年包月（优惠）
   - **地域**：选择离你近的
   - **实例**：
     - 标准型 S5.MEDIUM2（2核2GB）- 最低配置
     - 标准型 S5.MEDIUM4（2核4GB）- 推荐
   - **镜像**：Ubuntu Server 20.04 LTS 64位
   - **系统盘**：50GB SSD
   - **公网带宽**：按流量计费，峰值5Mbps
   - **安全组**：新建安全组，允许SSH(22)
   - **价格**：约 ¥150-300/月

### Step 2: 购买云数据库

#### PostgreSQL 云数据库
1. 进入 [云数据库 PostgreSQL](https://console.cloud.tencent.com/postgres)
2. 点击「新建」：
   - **地域**：与CVM相同
   - **数据库版本**：PostgreSQL 12
   - **实例规格**：1核1GB（入门配置）
   - **存储空间**：20GB
   - **网络**：选择与CVM相同的VPC
   - **价格**：约 ¥60/月

3. 购买后记录：
   - 内网地址（如：10.0.0.5）
   - 端口（默认5432）
   - 用户名/密码

#### Redis 云数据库（可选）
1. 进入 [云数据库 Redis](https://console.cloud.tencent.com/redis)
2. 点击「新建」：
   - **地域**：与CVM相同
   - **版本**：5.0
   - **规格**：1GB标准版
   - **网络**：选择与CVM相同的VPC
   - **价格**：约 ¥30/月

或者使用 CVM 自带的 Redis（省钱方案）

### Step 3: 配置网络安全

#### CVM 安全组
```
类型      协议    端口范围    源地址        策略
SSH       TCP    22         0.0.0.0/0    允许
ICMP      ICMP   -          0.0.0.0/0    允许
```

#### PostgreSQL 安全组
```
类型         协议    端口    源地址           策略
PostgreSQL   TCP    5432    CVM的内网IP     允许
```

#### Redis 安全组（如使用云Redis）
```
类型      协议    端口    源地址           策略
Redis     TCP    6379    CVM的内网IP     允许
```

### Step 4: 连接并配置CVM

```bash
# SSH 连接
ssh ubuntu@你的CVM公网IP

# 切换到 root（如需要）
sudo -i

# 更新系统
apt update && apt upgrade -y

# 安装依赖
apt install -y python3.9 python3.9-venv python3-pip git supervisor redis-server

# 如果使用云Redis，可以不安装 redis-server
```

### Step 5: 初始化云数据库

#### PostgreSQL（使用云数据库）
```bash
# 安装 PostgreSQL 客户端
apt install -y postgresql-client

# 连接到云数据库（使用内网地址）
psql -h 10.0.0.5 -U postgres -d postgres

# 创建数据库和用户
CREATE USER cryptobot WITH PASSWORD 'your_strong_password';
CREATE DATABASE crypto_monitor OWNER cryptobot;
GRANT ALL PRIVILEGES ON DATABASE crypto_monitor TO cryptobot;
\q
```

### Step 6: 部署项目

```bash
# 1. 创建项目目录
mkdir -p /opt/crypto-monitor-bot
cd /opt/crypto-monitor-bot

# 2. 克隆或上传代码
git clone https://github.com/your-username/crypto-monitor-bot.git .

# 3. 创建虚拟环境
python3.9 -m venv venv
source venv/bin/activate

# 4. 安装依赖
pip install --upgrade pip
pip install -r requirements.txt

# 5. 配置环境变量
cp .env.example .env
nano .env
```

**编辑 .env（云数据库版本）**：
```bash
# Telegram Bot
TELEGRAM_BOT_TOKEN=你的Token
TELEGRAM_CHAT_ID=你的ChatID

# PostgreSQL 云数据库（使用内网地址）
POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=你的云数据库密码
POSTGRES_DB=crypto_monitor
DATABASE_URL=postgresql://cryptobot:你的密码@10.0.0.5:5432/crypto_monitor

# Redis（使用云Redis或本地Redis）
# 云Redis:
REDIS_PASSWORD=云Redis密码
REDIS_URL=redis://:云Redis密码@10.0.0.6:6379/0

# 本地Redis:
# REDIS_PASSWORD=本地Redis密码
# REDIS_URL=redis://:本地Redis密码@localhost:6379/0

LOG_LEVEL=INFO
```

### Step 7-9: 测试、配置自启动、管理命令

参考方案一的 Step 7-9 步骤。

---

## 📊 部署后验证

### 1. 检查服务状态
```bash
supervisorctl status crypto-monitor-bot
# 期望输出: RUNNING
```

### 2. 检查日志
```bash
tail -f /var/log/crypto-monitor-bot.log
```

应该看到：
```
✅ Database connections established
✅ Selected 50 symbols
✅ Subscribed to 50 symbols
✅ Bot is running!
```

### 3. 测试 Telegram 告警
```bash
# 等待价格波动，或手动测试
cd /opt/crypto-monitor-bot
source venv/bin/activate
python test_telegram.py
```

### 4. 监控系统资源
```bash
# 查看内存使用
free -h

# 查看CPU使用
htop

# 查看磁盘使用
df -h

# 查看进程
ps aux | grep python
```

---

## 🔧 常见问题排查

### 问题1: 无法连接到数据库

**检查**：
```bash
# 测试 PostgreSQL 连接
psql -h localhost -U cryptobot -d crypto_monitor

# 测试 Redis 连接
redis-cli -a 你的Redis密码 ping
# 应返回: PONG
```

**解决**：
- 检查数据库服务是否运行：`systemctl status postgresql redis`
- 检查防火墙规则
- 检查 .env 配置是否正确

### 问题2: 程序启动后立即停止

**检查**：
```bash
# 查看详细日志
tail -n 100 /var/log/crypto-monitor-bot.log

# 手动运行查看错误
cd /opt/crypto-monitor-bot
source venv/bin/activate
python main.py
```

常见原因：
- Telegram Token 错误
- 数据库连接失败
- 依赖包未安装完整

### 问题3: 无法接收 Telegram 消息

**检查**：
1. Bot Token 是否正确
2. Chat ID 是否正确
3. 是否已向机器人发送过 /start
4. 服务器网络是否正常

```bash
# 测试网络连接
curl https://api.telegram.org

# 测试 Telegram API
curl https://api.telegram.org/bot你的Token/getMe
```

---

## 🛡️ 安全加固（生产环境必做）

### 1. 修改 SSH 端口
```bash
nano /etc/ssh/sshd_config
# 修改 Port 22 为其他端口（如 2222）
systemctl restart sshd
```

### 2. 禁用 root 密码登录
```bash
# 创建普通用户
adduser ubuntu
usermod -aG sudo ubuntu

# 配置 SSH 密钥登录
# 禁用密码登录
nano /etc/ssh/sshd_config
# 设置: PermitRootLogin no
#      PasswordAuthentication no
```

### 3. 配置防火墙
```bash
# 使用 UFW 防火墙
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

### 4. 定期备份数据库
```bash
# 创建备份脚本
nano /opt/backup_db.sh
```

```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups"
mkdir -p $BACKUP_DIR

# 备份 PostgreSQL
pg_dump -h localhost -U cryptobot crypto_monitor > $BACKUP_DIR/db_$DATE.sql

# 保留最近7天的备份
find $BACKUP_DIR -name "db_*.sql" -mtime +7 -delete

echo "Backup completed: db_$DATE.sql"
```

```bash
chmod +x /opt/backup_db.sh

# 添加定时任务（每天凌晨3点备份）
crontab -e
# 添加: 0 3 * * * /opt/backup_db.sh
```

---

## 📈 性能优化建议

### 1. 升级服务器配置（如需要）
- CPU: 2核 → 4核（处理更多币种）
- 内存: 2GB → 4GB（降低内存压力）
- 带宽: 3Mbps → 5Mbps（更快的API响应）

### 2. 数据库优化
```sql
-- 为常用查询创建索引
CREATE INDEX idx_prices_symbol_time ON prices(symbol, timestamp DESC);
CREATE INDEX idx_alerts_time ON alerts(created_at DESC);

-- 清理旧数据
DELETE FROM prices WHERE timestamp < NOW() - INTERVAL '180 days';
```

### 3. Redis 优化
```bash
# 编辑 Redis 配置
nano /etc/redis/redis.conf

# 设置最大内存
maxmemory 512mb
maxmemory-policy allkeys-lru
```

---

## 💰 成本估算

### 方案一（轻量应用服务器）
| 项目 | 配置 | 月费用 |
|------|------|--------|
| 轻量服务器 | 2核2GB | ¥50-80 |
| **总计** | | **¥50-80** |

### 方案二（云服务器 + 云数据库）
| 项目 | 配置 | 月费用 |
|------|------|--------|
| CVM | 2核4GB | ¥150-300 |
| PostgreSQL | 1核1GB | ¥60 |
| Redis（可选） | 1GB | ¥30 |
| **总计** | | **¥240-390** |

---

## 🎯 下一步

1. **监控运行状态**：定期查看日志和系统资源
2. **调整告警阈值**：根据实际需求修改 `config.yaml`
3. **扩展监控币种**：修改 `config.yaml` 中的 `max_count`
4. **启用主动交易策略**（可选）：参考 `docs/strategies/pump-dump-trading.md`

---

## 📞 需要帮助？

- 📖 查看文档: [README.md](README.md)
- 💬 提交问题: [GitHub Issues](https://github.com/your-repo/issues)
- 📧 联系作者: your-email@example.com

---

**部署完成！** 🎉

你的加密货币监控机器人现在应该已经在腾讯云上稳定运行了。
