# 🚀 腾讯云部署 - 5分钟快速开始

最快的方式让你的加密货币监控机器人在腾讯云上运行起来。

---

## ⚡ 超快速部署（推荐）

### Step 1: 购买服务器（2分钟）

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
2. 搜索「轻量应用服务器」或「云服务器CVM」
3. 点击「新建」，选择：
   - **镜像**: Ubuntu 20.04
   - **套餐**: 2核2GB（最低配置）
   - **地域**: 选择离你近的
4. 点击「立即购买」
5. **记录下服务器的公网IP**

### Step 2: 连接到服务器（1分钟）

**方法1: 网页终端（最简单）**
- 在控制台点击实例名称 → 点击「登录」→ 选择「浏览器 VNC 登录」

**方法2: SSH（推荐）**
```bash
ssh root@你的服务器IP
# 输入密码（购买时设置的）
```

### Step 3: 一键部署（2分钟）

```bash
# 下载部署脚本
wget https://raw.githubusercontent.com/your-repo/crypto-monitor-bot/main/deploy_tencent_cloud.sh

# 或者如果 GitHub 访问慢，使用以下命令创建脚本
# （将下面的内容保存为 deploy.sh）

# 运行部署脚本
bash deploy_tencent_cloud.sh
```

**按照提示输入**：
1. PostgreSQL 密码（自己设置一个强密码）
2. Redis 密码（自己设置一个强密码）
3. Telegram Bot Token（从 @BotFather 获取）
4. Telegram Chat ID（从 @userinfobot 获取）

脚本会自动完成：
- ✅ 安装所有依赖（Python、PostgreSQL、Redis）
- ✅ 配置数据库
- ✅ 部署项目代码
- ✅ 配置开机自启动
- ✅ 启动监控服务

### Step 4: 验证运行（1分钟）

```bash
# 查看服务状态
supervisorctl status crypto-monitor-bot
# 应显示: RUNNING

# 查看实时日志
tail -f /var/log/crypto-monitor-bot.log

# 应该看到:
# ✅ Database connections established
# ✅ Selected 50 symbols
# ✅ Bot is running!
```

🎉 **完成！** 你的机器人已经开始监控了，等待价格波动时会在Telegram收到告警。

---

## 📋 获取 Telegram Bot Token 和 Chat ID

### 获取 Bot Token（1分钟）

1. 在 Telegram 搜索 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot`
3. 按提示设置机器人名称和用户名
4. 复制 Bot Token（格式：`123456789:ABCdefGHIjklMNOpqrsTUVwxyz`）

### 获取 Chat ID（30秒）

**方法1: 使用机器人**
1. 在 Telegram 搜索 [@userinfobot](https://t.me/userinfobot)
2. 发送 `/start`
3. 复制 Chat ID（格式：`123456789`）

**方法2: 使用API**
1. 向你的机器人发送一条消息（任意内容）
2. 访问：`https://api.telegram.org/bot你的Token/getUpdates`
3. 查找 `"chat":{"id":123456789}`

**重要**: 一定要先给你的机器人发送 `/start` 命令！

---

## 🎯 手动部署（如果自动脚本失败）

### 1. 更新系统并安装依赖

```bash
# 更新系统
apt update && apt upgrade -y

# 安装依赖
apt install -y python3.9 python3.9-venv python3-pip \
               postgresql postgresql-contrib \
               redis-server git supervisor
```

### 2. 配置 PostgreSQL

```bash
# 切换到 postgres 用户
sudo -u postgres psql

# 执行以下 SQL（修改密码）
CREATE USER cryptobot WITH PASSWORD 'your_password_here';
CREATE DATABASE crypto_monitor OWNER cryptobot;
GRANT ALL PRIVILEGES ON DATABASE crypto_monitor TO cryptobot;
\q
```

### 3. 配置 Redis

```bash
# 编辑配置文件
nano /etc/redis/redis.conf

# 找到并修改（取消注释）
requirepass your_redis_password_here

# 重启 Redis
systemctl restart redis
systemctl enable redis
```

### 4. 部署项目

```bash
# 创建项目目录
mkdir -p /opt/crypto-monitor-bot
cd /opt/crypto-monitor-bot

# 克隆代码（或使用 scp 上传）
git clone https://github.com/your-username/crypto-monitor-bot.git .

# 创建虚拟环境
python3.9 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 创建配置文件
cp .env.example .env
nano .env
```

### 5. 编辑 .env 文件

```bash
TELEGRAM_BOT_TOKEN=你的Token
TELEGRAM_CHAT_ID=你的ChatID

POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=你的PostgreSQL密码
POSTGRES_DB=crypto_monitor
DATABASE_URL=postgresql://cryptobot:你的密码@localhost:5432/crypto_monitor

REDIS_PASSWORD=你的Redis密码
REDIS_URL=redis://:你的密码@localhost:6379/0

LOG_LEVEL=INFO
```

### 6. 测试运行

```bash
cd /opt/crypto-monitor-bot
source venv/bin/activate
python main.py

# 应该看到:
# ✅ Database connections established
# ✅ Selected 50 symbols
# ✅ Bot is running!

# 按 Ctrl+C 停止
```

### 7. 配置开机自启动

```bash
# 创建 Supervisor 配置
nano /etc/supervisor/conf.d/crypto-monitor-bot.conf
```

**粘贴以下内容**：
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
# 启动服务
supervisorctl reread
supervisorctl update
supervisorctl start crypto-monitor-bot

# 查看状态
supervisorctl status
```

---

## 🔍 常用命令

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
# 查看实时日志
tail -f /var/log/crypto-monitor-bot.log

# 查看最近100行
tail -n 100 /var/log/crypto-monitor-bot.log

# 搜索错误
grep ERROR /var/log/crypto-monitor-bot.log
```

### 系统监控
```bash
# 查看内存使用
free -h

# 查看CPU和进程
htop

# 查看磁盘使用
df -h

# 查看网络连接
netstat -tulpn
```

### 数据库操作
```bash
# 连接到 PostgreSQL
psql -U cryptobot -d crypto_monitor

# 查看表
\dt

# 查看最近的价格数据
SELECT * FROM prices ORDER BY timestamp DESC LIMIT 10;

# 查看告警历史
SELECT * FROM alerts ORDER BY created_at DESC LIMIT 10;

# 退出
\q
```

---

## ⚠️ 常见问题

### 1. 无法连接到数据库

**检查**：
```bash
# 测试 PostgreSQL
systemctl status postgresql

# 测试连接
psql -U cryptobot -d crypto_monitor

# 测试 Redis
systemctl status redis
redis-cli -a 你的密码 ping
```

### 2. 无法收到 Telegram 消息

**检查清单**：
- [ ] Bot Token 正确（从 @BotFather 获取）
- [ ] Chat ID 正确（从 @userinfobot 获取）
- [ ] 已向机器人发送 `/start`
- [ ] 服务器可以访问外网

**测试网络**：
```bash
curl https://api.telegram.org
curl https://api.telegram.org/bot你的Token/getMe
```

### 3. 服务一直重启

**查看错误日志**：
```bash
tail -n 100 /var/log/crypto-monitor-bot.log
```

**常见原因**：
- 数据库连接失败 → 检查密码和连接字符串
- Telegram Token 错误 → 检查 .env 文件
- 依赖包缺失 → 重新安装：`pip install -r requirements.txt`

### 4. 修改配置后不生效

**重启服务**：
```bash
supervisorctl restart crypto-monitor-bot
```

---

## 🎨 自定义配置

### 修改监控币种数量

```bash
nano /opt/crypto-monitor-bot/config.yaml

# 修改:
symbols:
  max_count: 100  # 从50改为100
```

### 修改告警阈值

```bash
nano /opt/crypto-monitor-bot/config.yaml

# 修改:
volatility:
  warning_threshold: 5.0   # 从10%改为5%
  critical_threshold: 15.0 # 从20%改为15%
```

**修改后记得重启**：
```bash
supervisorctl restart crypto-monitor-bot
```

---

## 📊 成本估算

### 轻量应用服务器
- **配置**: 2核2GB，3Mbps带宽
- **月费用**: ¥50-80
- **适合**: 个人使用、50-100币种监控

### 云服务器 + 云数据库
- **配置**: 2核4GB CVM + 1核1GB PostgreSQL
- **月费用**: ¥200-400
- **适合**: 生产环境、100+币种监控

---

## 🔐 安全建议

### 1. 修改 SSH 端口（可选）
```bash
nano /etc/ssh/sshd_config
# 修改: Port 22 为 Port 2222
systemctl restart sshd
```

### 2. 配置防火墙
```bash
ufw allow 22/tcp
ufw enable
```

### 3. 定期更新系统
```bash
apt update && apt upgrade -y
```

### 4. 定期备份数据库
```bash
# 手动备份
pg_dump -U cryptobot crypto_monitor > backup_$(date +%Y%m%d).sql

# 或使用自动备份脚本（见完整文档）
```

---

## 📚 更多文档

- 📖 [完整部署指南](TENCENT_CLOUD_DEPLOYMENT.md) - 详细步骤和高级配置
- 🚀 [快速开始](GETTING_STARTED.md) - 本地运行和测试
- 🎯 [功能介绍](docs/FEATURES.md) - 了解所有功能
- 🔧 [配置指南](docs/CONFIGURATION.md) - 详细配置选项
- 🐛 [故障排查](docs/TROUBLESHOOTING.md) - 问题诊断

---

## 📞 需要帮助？

- 💬 提交问题: [GitHub Issues](https://github.com/your-repo/issues)
- 📧 联系作者: your-email@example.com
- 📖 查看文档: [docs/](docs/)

---

## ✅ 部署检查清单

部署完成后，确保以下所有项都正常：

- [ ] 服务状态为 RUNNING：`supervisorctl status`
- [ ] 日志中显示 "Bot is running!"
- [ ] 可以连接到数据库：`psql -U cryptobot -d crypto_monitor`
- [ ] Redis 正常运行：`redis-cli ping`
- [ ] Telegram 机器人可以发送测试消息
- [ ] 服务器可以访问 Binance API
- [ ] 系统资源充足（内存 < 80%，CPU < 80%）

---

**部署成功！** 🎉

现在你的加密货币监控机器人已经在腾讯云上稳定运行了。

等待市场波动，你会在 Telegram 收到实时告警！

---

**快速参考卡**

| 操作 | 命令 |
|------|------|
| 查看状态 | `supervisorctl status` |
| 查看日志 | `tail -f /var/log/crypto-monitor-bot.log` |
| 重启服务 | `supervisorctl restart crypto-monitor-bot` |
| 连接数据库 | `psql -U cryptobot -d crypto_monitor` |
| 查看内存 | `free -h` |
| 修改配置 | `nano /opt/crypto-monitor-bot/.env` |
