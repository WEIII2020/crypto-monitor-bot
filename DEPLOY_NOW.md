# 🚀 立即部署到腾讯云

## 3 步完成部署

### 步骤 1: 配置服务器信息（1分钟）

```bash
# 编辑部署脚本
vim deploy.sh

# 修改这3个变量：
SERVER_HOST="your.server.ip"      # 改成您的服务器 IP
SERVER_USER="root"                 # SSH 用户名
SERVER_PORT="22"                   # SSH 端口
```

### 步骤 2: 执行一键部署（3-5分钟）

```bash
# 确保有执行权限
chmod +x deploy.sh

# 执行部署
./deploy.sh

# 部署过程会自动：
# ✅ 测试 SSH 连接
# ✅ 同步代码到服务器
# ✅ 安装 Python 依赖
# ✅ 创建 systemd 服务
# ✅ 配置运行环境
```

### 步骤 3: 配置并启动（2分钟）

```bash
# SSH 登录服务器
ssh root@your_server_ip

# 进入目录
cd /root/crypto-monitor-bot

# 配置 Telegram（必需）
vim .env
# 添加：
# export TELEGRAM_BOT_TOKEN="your_token"
# export TELEGRAM_CHAT_ID="your_chat_id"

# 启动服务
systemctl start crypto-monitor-bot

# 查看状态
systemctl status crypto-monitor-bot

# 查看日志
tail -f logs/bot.log
```

---

## ✅ 部署完成！

**服务管理命令：**

```bash
# 使用管理脚本（推荐）
./manage.sh start      # 启动
./manage.sh stop       # 停止
./manage.sh restart    # 重启
./manage.sh status     # 状态
./manage.sh logs follow # 实时日志
./manage.sh diagnose   # 诊断

# 或使用 systemctl
systemctl start crypto-monitor-bot
systemctl stop crypto-monitor-bot
systemctl restart crypto-monitor-bot
systemctl status crypto-monitor-bot
```

**查看日志：**

```bash
# 实时日志
tail -f /root/crypto-monitor-bot/logs/bot.log

# 最近的信号
grep "NEW SIGNAL" /root/crypto-monitor-bot/logs/bot.log | tail -10

# 错误日志
tail -f /root/crypto-monitor-bot/logs/bot.error.log
```

---

## 📝 获取 Telegram 配置

### 1. 获取 Bot Token

1. 打开 Telegram，搜索 `@BotFather`
2. 发送 `/newbot`
3. 按提示设置 Bot 名称
4. 获得 Token：`6123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### 2. 获取 Chat ID

1. 搜索 `@userinfobot`
2. 发送任意消息
3. 获得 Chat ID：`123456789`

---

## ⚠️ 重要提示

1. **首次运行建议测试模式**：
   ```bash
   # 编辑配置文件
   vim /root/crypto-monitor-bot/config/config.yaml
   # 设置: test_mode: true
   ```

2. **自动交易默认关闭**：
   ```yaml
   trading:
     enabled: false  # 默认关闭，谨慎启用
   ```

3. **冷启动期**：
   - V4A 策略：立即可用 ✅
   - V8 策略：30 分钟后 ⏳
   - LONG 策略：1 小时后 ⏳
   - V7 策略：4 小时后 ⏳

---

## 📚 完整文档

- `DEPLOYMENT_GUIDE.md` - 详细部署指南
- `README_MERGED.md` - 完整功能文档
- `QUICKSTART.md` - 快速开始指南

---

## 🎉 开始部署

```bash
./deploy.sh
```

**部署时间：约 5-10 分钟**

如有问题，请查看 `DEPLOYMENT_GUIDE.md` 的常见问题部分。
