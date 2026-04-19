# 🚀 腾讯云部署指南

完整的腾讯云服务器部署教程。

---

## 🚀 快速部署（推荐）

### 1. 配置部署脚本

```bash
vim deploy.sh

# 修改以下变量
SERVER_HOST="your.server.ip"      # 您的服务器 IP
SERVER_USER="root"                 # SSH 用户名
SERVER_PORT="22"                   # SSH 端口
```

### 2. 执行一键部署

```bash
./deploy.sh
```

### 3. 配置环境变量

```bash
# SSH 登录服务器
ssh root@your_server_ip
cd /root/crypto-monitor-bot

# 编辑环境变量
vim .env
```

添加：
```bash
export TELEGRAM_BOT_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

### 4. 启动服务

```bash
systemctl start crypto-monitor-bot
systemctl status crypto-monitor-bot
tail -f logs/bot.log
```

---

## 📚 完整文档

详细的部署步骤、配置说明、服务管理、常见问题解决，请查看完整版部署指南。

**立即部署：**
```bash
./deploy.sh
```
