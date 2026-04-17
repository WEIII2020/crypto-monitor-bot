# 🚀 手动部署指南 - v2.0-unified-200

> 因为 SSH 需要密码认证，这里提供完整的手动部署步骤

---

## ✅ 步骤 1: 打包代码（已完成）

代码已经打包完成：
```
文件位置: /tmp/crypto-bot-v2.0.tar.gz
文件大小: 412K
```

---

## 📤 步骤 2: 上传到服务器

### 方法 A: 使用 SCP（推荐）

在**本地终端**执行：

```bash
scp /tmp/crypto-bot-v2.0.tar.gz root@119.28.43.237:/root/
```

**输入服务器密码**后等待上传完成。

### 方法 B: 使用 FTP 工具（图形界面）

如果 SCP 有问题，可以使用图形界面工具：

1. **Transmit** (Mac)
2. **FileZilla** (跨平台)
3. **Cyberduck** (Mac/Windows)

连接信息：
- 主机: `119.28.43.237`
- 用户: `root`
- 端口: `22`
- 协议: `SFTP`

上传文件 `/tmp/crypto-bot-v2.0.tar.gz` 到服务器的 `/root/` 目录。

---

## 🖥️ 步骤 3: 在服务器上部署

### 3.1 SSH 登录服务器

```bash
ssh root@119.28.43.237
```

输入密码登录。

### 3.2 执行部署命令

登录成功后，**直接复制粘贴以下所有命令**（一次性执行）：

```bash
# ============================================
# 服务器部署脚本 - 直接复制粘贴执行
# ============================================

# 1. 备份旧版本
if [ -d "/root/crypto-monitor-bot" ]; then
    echo "🔄 备份旧版本..."
    mkdir -p /root/backups
    BACKUP_NAME="crypto-bot-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    cd /root
    tar -czf backups/${BACKUP_NAME} crypto-monitor-bot
    echo "✅ 备份完成: backups/${BACKUP_NAME}"
    
    # 保存 .env
    if [ -f "/root/crypto-monitor-bot/.env" ]; then
        cp /root/crypto-monitor-bot/.env /tmp/.env.backup
        echo "✅ 已保存 .env 配置"
    fi
    
    # 停止旧服务
    cd /root/crypto-monitor-bot
    if [ -f "check_bot_status.sh" ]; then
        ./check_bot_status.sh stop 2>/dev/null || true
    fi
    pkill -f "python.*main.py" 2>/dev/null || true
    echo "🛑 已停止旧服务"
fi

# 2. 清理并解压新版本
echo "📦 部署新版本..."
cd /root
rm -rf /root/crypto-monitor-bot
mkdir -p /root/crypto-monitor-bot
tar -xzf /root/crypto-bot-v2.0.tar.gz -C /root/crypto-monitor-bot
echo "✅ 解压完成"

# 3. 恢复 .env
cd /root/crypto-monitor-bot
if [ -f "/tmp/.env.backup" ]; then
    mv /tmp/.env.backup .env
    echo "✅ 恢复 .env 配置"
else
    echo "⚠️  创建新的 .env 文件"
    cp .env.example .env
    echo ""
    echo "⚠️  重要: 请编辑 .env 文件填入你的配置"
    echo "   vim .env"
    echo ""
fi

# 4. 设置权限
chmod +x *.sh 2>/dev/null || true
echo "✅ 权限设置完成"

# 5. 创建虚拟环境
echo "📦 创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 6. 安装依赖
echo "📦 安装依赖包（可能需要几分钟）..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

echo ""
echo "==============================================="
echo "🎉 部署完成！"
echo "==============================================="
echo ""
echo "版本信息:"
echo "  版本: v2.0-unified-200"
echo "  监控币种: 200 个"
echo "  部署时间: $(date)"
echo ""
echo "📊 验证安装:"
echo ""

# 验证配置
echo "1️⃣ 配置文件:"
cat config.yaml | head -7

echo ""
echo "2️⃣ Python 包:"
source venv/bin/activate
pip list | grep -E "ccxt|websockets|asyncpg|redis|python-telegram"

echo ""
echo "==============================================="
echo "📝 下一步操作:"
echo "==============================================="
echo ""
echo "1. 【必须】检查/编辑配置文件:"
echo "   vim .env"
echo ""
echo "   需要配置的关键项:"
echo "   - POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD"
echo "   - REDIS_HOST"
echo "   - TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID"
echo ""
echo "2. 启动服务:"
echo "   ./start.sh"
echo ""
echo "3. 查看日志:"
echo "   tail -f logs/crypto_monitor_*.log"
echo ""
echo "4. 检查状态:"
echo "   ./check_bot_status.sh"
echo ""
echo "==============================================="
```

---

## 🎯 步骤 4: 配置环境变量

部署完成后，**必须配置 .env 文件**：

```bash
# 在服务器上执行
cd /root/crypto-monitor-bot
vim .env
```

**必须配置的项**：

```bash
# 数据库配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=crypto_monitor
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Telegram Bot
TELEGRAM_BOT_TOKEN=你的bot_token
TELEGRAM_USER_ID=你的user_id
```

保存后退出（`:wq`）。

---

## 🚀 步骤 5: 启动服务

```bash
cd /root/crypto-monitor-bot
./start.sh
```

---

## ✅ 步骤 6: 验证运行

### 6.1 查看日志

```bash
tail -f logs/crypto_monitor_*.log
```

应该看到类似输出：
```
🚀 Starting Crypto Monitor Bot...
✅ Database connections established
📊 Selecting optimal symbols for monitoring...
✅ Selected 200 symbols
   Preview: BTCUSDT, ETHUSDT, BNBUSDT, ...
✅ Subscribed to 200 symbols
✅ Bot is running! Press Ctrl+C to stop.
```

按 `Ctrl+C` 退出日志查看（服务继续运行）。

### 6.2 检查进程

```bash
ps aux | grep python | grep main.py
```

应该看到 Python 进程在运行。

### 6.3 测试 Telegram

给你的 Telegram Bot 发送消息，确认能收到响应。

---

## 📊 监控与管理

### 查看实时日志
```bash
tail -f logs/crypto_monitor_*.log
```

### 检查状态
```bash
cd /root/crypto-monitor-bot
./check_bot_status.sh
```

### 重启服务
```bash
./check_bot_status.sh restart
```

### 停止服务
```bash
./check_bot_status.sh stop
```

---

## 🐛 常见问题

### 问题 1: 上传文件失败

**解决方案 A**: 确认密码正确
```bash
ssh root@119.28.43.237  # 先测试SSH登录
```

**解决方案 B**: 使用图形界面工具（FileZilla, Transmit）

### 问题 2: Python 包安装失败

```bash
# 更新 pip
source venv/bin/activate
pip install --upgrade pip

# 重试安装
pip install -r requirements.txt
```

### 问题 3: 数据库连接失败

检查数据库是否运行：
```bash
systemctl status postgresql
systemctl status redis
```

### 问题 4: 200 币种占用资源太高

临时降低币种数量：
```bash
vim config.yaml

# 修改
symbols:
  max_count: 100  # 先测试 100 个

# 重启
./check_bot_status.sh restart
```

---

## 📞 需要帮助？

如果遇到问题，提供以下信息：

1. 错误日志：
```bash
tail -100 logs/crypto_monitor_*.log
```

2. 系统资源：
```bash
free -h
df -h
```

3. 进程状态：
```bash
ps aux | grep python
```

---

## 🎉 部署完成！

恭喜！你的 v2.0-unified-200 版本已成功部署！

**现在可以监控 200 个币种了！** 🚀

---

**有任何问题随时问我！** 💪
