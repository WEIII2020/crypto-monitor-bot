# 🚀 使用 Gitee + 网页终端部署指南

**最适合国内用户的部署方式**

---

## 📋 准备工作

```
✅ 腾讯云服务器: 119.28.43.237
✅ Telegram Bot Token: 8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68
✅ Telegram Chat ID: 6954384980
✅ 配置信息已准备好
```

---

## 第一步：推送代码到 Gitee（5分钟）

### 1.1 注册 Gitee 账号

如果还没有 Gitee 账号：
1. 访问 https://gitee.com/
2. 点击「注册」
3. 填写邮箱、用户名、密码
4. 验证邮箱

### 1.2 创建仓库

1. 登录 Gitee
2. 点击右上角 `+` → 「新建仓库」
3. 填写信息：
   - 仓库名称：`crypto-monitor-bot`
   - 路径：自动生成
   - 是否开源：选择「私有」✅（重要！保护你的配置）
   - 初始化仓库：不勾选任何选项
4. 点击「创建」

### 1.3 在本地推送代码

**打开 Mac 终端，复制粘贴执行**：

```bash
# 进入项目目录
cd "/Users/szld2403203/Library/Mobile Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot"

# 创建 .gitignore（保护敏感信息）
cat > .gitignore << 'GITIGNORE'
.env
.env.local
*.log
bot.pid
venv/
__pycache__/
*.pyc
.DS_Store
*.sqlite
*.db
.idea/
.vscode/
GITIGNORE

# 添加所有文件
git add .

# 提交
git commit -m "Initial commit for Tencent Cloud deployment"

# 添加 Gitee 远程仓库（⚠️ 替换 YOUR_GITEE_USERNAME 为你的用户名）
git remote add origin https://gitee.com/YOUR_GITEE_USERNAME/crypto-monitor-bot.git

# 推送到 Gitee
git push -u origin main
```

**如果提示输入用户名和密码**：
- 用户名：你的 Gitee 用户名
- 密码：你的 Gitee 密码（或私人令牌）

### 1.4 确认推送成功

在浏览器打开：`https://gitee.com/YOUR_GITEE_USERNAME/crypto-monitor-bot`

应该能看到所有项目文件。

---

## 第二步：登录腾讯云网页终端（2分钟）

### 2.1 打开控制台

1. 访问 https://console.cloud.tencent.com/lighthouse/instance
2. 如果未登录，先登录腾讯云账号

### 2.2 找到你的服务器

1. 在实例列表中找到 IP 为 `119.28.43.237` 的服务器
2. 点击服务器名称或「详情」

### 2.3 打开网页终端

1. 点击页面上的「登录」按钮
2. 在下拉菜单中选择「浏览器 VNC 登录」
3. 稍等片刻，会打开一个黑色终端窗口
4. 看到类似 `root@VM-xxx:~#` 的提示符

---

## 第三步：一键部署（10分钟）

### 3.1 复制部署命令

**在网页终端中，复制粘贴以下完整命令**：

（⚠️ 记得替换 `YOUR_GITEE_USERNAME` 为你的 Gitee 用户名）

```bash
#!/bin/bash
set -e

# ============================================
# 配置区域
# ============================================

# ⚠️ 修改为你的 Gitee 仓库地址
REPO_URL="https://gitee.com/YOUR_GITEE_USERNAME/crypto-monitor-bot.git"

# Telegram 配置（已预设）
TELEGRAM_TOKEN="8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68"
TELEGRAM_CHAT_ID="6954384980"

# 数据库配置（已预设）
PG_PASSWORD="P@ssw0rd2024!Crypto#DB"
REDIS_PASSWORD="R3dis\$Secure#2024Pass!"

# ============================================
# 自动部署开始
# ============================================

echo "🚀 开始自动部署 Crypto Monitor Bot"
echo "📦 仓库: $REPO_URL"
echo ""

# 1. 安装系统依赖
echo "📦 [1/8] 安装系统依赖..."
export DEBIAN_FRONTEND=noninteractive
apt update -qq
apt install -y -qq \
    python3.9 python3.9-venv python3-pip \
    postgresql postgresql-contrib \
    redis-server supervisor git htop curl

echo "✅ 系统依赖安装完成"

# 2. 配置 PostgreSQL
echo "🗄️ [2/8] 配置 PostgreSQL..."
sudo -u postgres psql << PSQL_EOF
DROP DATABASE IF EXISTS crypto_monitor;
DROP USER IF EXISTS cryptobot;
CREATE USER cryptobot WITH PASSWORD '$PG_PASSWORD';
CREATE DATABASE crypto_monitor OWNER cryptobot;
GRANT ALL PRIVILEGES ON DATABASE crypto_monitor TO cryptobot;
\q
PSQL_EOF

PG_HBA=\$(find /etc/postgresql -name pg_hba.conf | head -1)
if ! grep -q "127.0.0.1/32.*md5" "\$PG_HBA"; then
    echo "host all all 127.0.0.1/32 md5" >> "\$PG_HBA"
fi

systemctl restart postgresql
systemctl enable postgresql

echo "✅ PostgreSQL 配置完成"

# 3. 配置 Redis
echo "💾 [3/8] 配置 Redis..."
cp /etc/redis/redis.conf /etc/redis/redis.conf.backup 2>/dev/null || true
sed -i "s/# requirepass.*/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
sed -i "s/^requirepass.*/requirepass $REDIS_PASSWORD/" /etc/redis/redis.conf
sed -i "s/^bind .*/bind 127.0.0.1/" /etc/redis/redis.conf

systemctl restart redis
systemctl enable redis

echo "✅ Redis 配置完成"

# 4. 克隆代码
echo "📥 [4/8] 克隆项目代码..."
if [ -d "/opt/crypto-monitor-bot" ]; then
    echo "⚠️  备份旧版本..."
    mv /opt/crypto-monitor-bot /opt/crypto-monitor-bot.backup.\$(date +%Y%m%d_%H%M%S)
fi

git clone \$REPO_URL /opt/crypto-monitor-bot
cd /opt/crypto-monitor-bot

echo "✅ 代码克隆完成"

# 5. 安装 Python 依赖
echo "🐍 [5/8] 安装 Python 依赖..."
python3.9 -m venv venv
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo "✅ Python 依赖安装完成"

# 6. 创建配置文件
echo "⚙️ [6/8] 创建配置文件..."
cat > .env << ENV_EOF
# Telegram Bot
TELEGRAM_BOT_TOKEN=$TELEGRAM_TOKEN
TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID

# Database
POSTGRES_USER=cryptobot
POSTGRES_PASSWORD=$PG_PASSWORD
POSTGRES_DB=crypto_monitor
DATABASE_URL=postgresql://cryptobot:$PG_PASSWORD@localhost:5432/crypto_monitor

# Redis
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URL=redis://:$REDIS_PASSWORD@localhost:6379/0

# Logging
LOG_LEVEL=INFO
ENV_EOF

chmod 600 .env

echo "✅ 配置文件创建完成"

# 7. 测试运行
echo "🧪 [7/8] 测试运行..."
timeout 10 venv/bin/python main.py 2>&1 | head -20 || true
echo ""

# 8. 配置 Supervisor
echo "🔧 [8/8] 配置开机自启动..."
cat > /etc/supervisor/conf.d/crypto-monitor-bot.conf << SUPERVISOR_EOF
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

supervisorctl reread
supervisorctl update
supervisorctl start crypto-monitor-bot

sleep 3

# 显示结果
echo ""
echo "═══════════════════════════════════════════════════"
echo "✅ 部署完成！"
echo "═══════════════════════════════════════════════════"
echo ""
echo "📊 服务状态:"
supervisorctl status crypto-monitor-bot
echo ""
echo "📝 常用命令:"
echo "  查看实时日志: tail -f /var/log/crypto-monitor-bot.log"
echo "  查看状态: supervisorctl status"
echo "  重启服务: supervisorctl restart crypto-monitor-bot"
echo "  停止服务: supervisorctl stop crypto-monitor-bot"
echo ""
echo "💬 下一步:"
echo "  1. 查看日志确认运行: tail -f /var/log/crypto-monitor-bot.log"
echo "  2. 检查 Telegram 是否收到消息"
echo "  3. 等待价格波动时会收到告警"
echo ""
echo "═══════════════════════════════════════════════════"
```

### 3.2 执行命令

1. 确认已替换 `YOUR_GITEE_USERNAME`
2. 在网页终端中右键点击 → 粘贴（或 Shift+Insert）
3. 按回车键执行
4. 等待 10-15 分钟，脚本会自动完成所有配置

### 3.3 观察输出

你会看到类似的输出：
```
🚀 开始自动部署 Crypto Monitor Bot
📦 [1/8] 安装系统依赖...
✅ 系统依赖安装完成
🗄️ [2/8] 配置 PostgreSQL...
✅ PostgreSQL 配置完成
💾 [3/8] 配置 Redis...
✅ Redis 配置完成
...
✅ 部署完成！
```

---

## 第四步：验证部署（2分钟）

### 4.1 查看服务状态

```bash
supervisorctl status crypto-monitor-bot
```

**期望输出**：
```
crypto-monitor-bot   RUNNING   pid 1234, uptime 0:01:00
```

### 4.2 查看实时日志

```bash
tail -f /var/log/crypto-monitor-bot.log
```

**期望看到**：
```
🚀 Starting Crypto Monitor Bot...
✅ Database connections established
✅ Selected 50 symbols
   Preview: BTCUSDT, ETHUSDT, BNBUSDT...
✅ Subscribed to 50 symbols
✅ Bot is running! Press Ctrl+C to stop.
```

按 `Ctrl+C` 退出日志查看。

### 4.3 检查 Telegram

打开 Telegram，检查是否收到机器人的消息。

如果没有收到，手动发送测试消息：

```bash
cd /opt/crypto-monitor-bot
source venv/bin/activate

python3 << 'EOF'
import asyncio
from dotenv import load_dotenv
from src.notifiers.telegram_notifier import TelegramNotifier

load_dotenv()

async def test():
    notifier = TelegramNotifier()
    await notifier.send_message("🎉 部署成功！监控已启动 ✅")

asyncio.run(test())
EOF
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
grep -i error /var/log/crypto-monitor-bot.log

# 搜索告警
grep "🚨" /var/log/crypto-monitor-bot.log
```

### 代码更新

如果修改了代码并推送到 Gitee，在服务器执行：

```bash
cd /opt/crypto-monitor-bot
git pull
source venv/bin/activate
pip install -r requirements.txt
supervisorctl restart crypto-monitor-bot
```

---

## 🔧 故障排查

### 问题1：Git clone 失败

**症状**：`fatal: unable to access 'https://gitee.com/...'`

**解决**：
```bash
# 测试网络
ping gitee.com

# 如果无法访问，使用 GitHub
# 或者检查仓库是否设为私有（需要配置访问令牌）
```

### 问题2：服务无法启动

```bash
# 查看详细错误
tail -n 50 /var/log/crypto-monitor-bot.log

# 手动运行查看错误
cd /opt/crypto-monitor-bot
source venv/bin/activate
python main.py
```

### 问题3：数据库连接失败

```bash
# 测试 PostgreSQL
psql -U cryptobot -d crypto_monitor -h localhost

# 如果无法连接，检查密码
cat /opt/crypto-monitor-bot/.env | grep POSTGRES

# 重置密码
sudo -u postgres psql -c "ALTER USER cryptobot PASSWORD 'P@ssw0rd2024!Crypto#DB';"
```

### 问题4：无法收到 Telegram 消息

```bash
# 测试网络
curl https://api.telegram.org

# 检查配置
cat /opt/crypto-monitor-bot/.env | grep TELEGRAM

# 手动发送测试（见上面 4.3 节）
```

---

## 📊 部署信息记录

```
═══════════════════════════════════════
  部署信息 - 请妥善保管
═══════════════════════════════════════

服务器:
  IP: 119.28.43.237
  登录: 腾讯云网页终端
  
项目:
  目录: /opt/crypto-monitor-bot
  日志: /var/log/crypto-monitor-bot.log
  Gitee: https://gitee.com/YOUR_USERNAME/crypto-monitor-bot
  
数据库:
  PostgreSQL: localhost:5432
  用户: cryptobot
  密码: P@ssw0rd2024!Crypto#DB
  
  Redis: localhost:6379
  密码: R3dis$Secure#2024Pass!
  
Telegram:
  Token: 8612731213:AAE...T68
  Chat ID: 6954384980

═══════════════════════════════════════
```

---

## 🎉 完成！

现在你的加密货币监控机器人已经在腾讯云上运行了！

**等待市场波动，你会在 Telegram 收到实时告警。** 📊

---

**需要帮助？** 查看 [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) 或提交 Issue。
