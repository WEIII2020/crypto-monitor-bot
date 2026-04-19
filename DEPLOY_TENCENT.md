# 🚀 腾讯云服务器部署指南

3 步快速部署到腾讯云服务器

---

## 📋 准备工作

### 1. 本地准备
- [x] 代码已推送到 GitHub
- [ ] 获取腾讯云服务器 IP
- [ ] 配置 SSH 密钥（推荐）
- [ ] 准备 Telegram Bot Token 和 Chat ID

### 2. 服务器要求
- **系统**: CentOS 7+, Ubuntu 18.04+, Debian 10+
- **内存**: 至少 2GB
- **磁盘**: 至少 10GB 可用空间
- **Python**: 3.10+（脚本会自动安装）

---

## 🎯 方式 1: 一键部署（推荐）

### Step 1: 配置服务器信息

```bash
# 编辑部署脚本
vim deploy_to_tencent.sh

# 修改以下三行：
SERVER_IP="your_server_ip_here"     # 改为实际 IP
SSH_USER="root"                     # 如果不是 root，修改这里
SSH_PORT="22"                       # 如果不是 22，修改这里
```

### Step 2: 配置 SSH 密钥（推荐）

```bash
# 将本地 SSH 密钥复制到服务器（只需执行一次）
ssh-copy-id -p 22 root@your_server_ip

# 测试连接
ssh root@your_server_ip "echo '连接成功'"
```

### Step 3: 执行一键部署

```bash
./deploy_to_tencent.sh
```

脚本会自动：
- ✅ 测试 SSH 连接
- ✅ 创建远程目录
- ✅ 同步所有代码
- ✅ 安装 Python 依赖
- ✅ 创建 systemd 服务
- ✅ 配置自动重启

---

## 🎯 方式 2: 手动部署

### Step 1: 登录服务器

```bash
ssh root@your_server_ip
```

### Step 2: 从 GitHub 克隆代码

```bash
cd /root
git clone https://github.com/WEIII2020/crypto-monitor-bot.git
cd crypto-monitor-bot
```

### Step 3: 执行服务器端部署

```bash
bash deploy.sh server
```

这会自动：
- 检查并安装 Python 3
- 创建虚拟环境
- 安装所有依赖
- 创建 systemd 服务

---

## ⚙️ 配置环境变量

### 创建 .env 文件

```bash
cd /root/crypto-monitor-bot
vim .env
```

### 最小配置（推荐先用这个测试）

```bash
# 粘贴以下内容到 .env 文件

# Telegram 配置
export TELEGRAM_BOT_TOKEN="你的_bot_token"
export TELEGRAM_CHAT_ID="你的_chat_id"

# 日志级别
export LOG_LEVEL="INFO"
```

### 获取 Telegram 配置

**1. 获取 Bot Token:**
```
1. 在 Telegram 搜索: @BotFather
2. 发送: /newbot
3. 按提示设置名称
4. 复制返回的 Token
```

**2. 获取 Chat ID:**
```
方式 1 - 个人 ID:
  1. 搜索: @userinfobot
  2. 发送任意消息
  3. 复制返回的 ID

方式 2 - 群组 ID:
  1. 创建群组，将你的 Bot 添加进去
  2. 在群组发送一条消息
  3. 浏览器访问:
     https://api.telegram.org/bot<你的Token>/getUpdates
  4. 在返回的 JSON 中找到 chat: {id: -123456789}
```

### 保存并设置权限

```bash
# 保存文件 (vim 中按 ESC 然后输入 :wq)

# 设置安全权限
chmod 600 .env

# 验证配置
cat .env
```

---

## 🚀 启动服务

### 启动 Bot

```bash
# 启动服务
systemctl start crypto-monitor-bot

# 查看状态
systemctl status crypto-monitor-bot

# 查看日志（实时）
tail -f /root/crypto-monitor-bot/logs/bot.log
```

### 检查是否正常运行

**1. 查看进程:**
```bash
ps aux | grep main_phase2.py
```

**2. 查看日志:**
```bash
tail -20 /root/crypto-monitor-bot/logs/bot.log
```

**3. 检查 Telegram:**
- 应该收到启动通知
- 应该开始收到信号推送

### 设置开机自启

```bash
systemctl enable crypto-monitor-bot
```

---

## 🛠️ 服务管理

使用便捷管理脚本：

```bash
cd /root/crypto-monitor-bot

# 查看状态
./manage.sh status

# 启动服务
./manage.sh start

# 停止服务
./manage.sh stop

# 重启服务
./manage.sh restart

# 查看日志
./manage.sh logs           # 普通日志
./manage.sh logs follow    # 实时日志
./manage.sh logs error     # 错误日志
./manage.sh logs signal    # 信号日志

# 系统诊断
./manage.sh diagnose

# 更新代码
./manage.sh update

# 清理日志
./manage.sh clean
```

---

## 🏥 启用 Hermes Agent（交互模式）

如果需要 Telegram 交互命令功能：

### 1. 创建新的 Bot（推荐）

```
1. 在 Telegram 找 @BotFather
2. /newbot
3. 创建名为 "YourName Hermes Agent" 的 Bot
4. 获取新的 Token
```

### 2. 更新 .env 配置

```bash
vim /root/crypto-monitor-bot/.env

# 添加这一行：
export HERMES_BOT_TOKEN="新的_bot_token"
```

### 3. 使用统一启动模式

修改 systemd 服务：

```bash
vim /etc/systemd/system/crypto-monitor-bot.service

# 找到 ExecStart 这行，改为：
ExecStart=/root/crypto-monitor-bot/run_with_monitoring.sh signal

# 保存后重新加载
systemctl daemon-reload
systemctl restart crypto-monitor-bot
```

### 4. 测试交互命令

在 Telegram 中向 Hermes Bot 发送：
```
/start      - 查看欢迎消息
/status     - 系统状态
/signals    - 最近信号
/health     - 健康检查
/help       - 帮助
```

---

## 📊 监控和维护

### 日常检查

```bash
# 每天检查一次
./manage.sh status
./manage.sh logs | tail -50

# 查看系统资源
free -h          # 内存
df -h            # 磁盘
top              # CPU
```

### 性能优化

如果服务器资源紧张，编辑配置：

```bash
vim /root/crypto-monitor-bot/config/config.yaml

# 减少监控币种
symbols_count: 100  # 从 200 改为 100

# 增加采集间隔
data_interval: 2    # 从 1 秒改为 2 秒
```

### 日志轮转

自动清理旧日志：

```bash
# 创建日志轮转配置
cat > /etc/logrotate.d/crypto-monitor-bot << 'EOF'
/root/crypto-monitor-bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
}
EOF

# 测试
logrotate -f /etc/logrotate.d/crypto-monitor-bot
```

---

## 🔐 安全建议

### 1. 防火墙配置

```bash
# 只开放必要端口
ufw allow 22/tcp   # SSH
ufw enable
ufw status
```

### 2. SSH 安全加固

```bash
vim /etc/ssh/sshd_config

# 推荐设置：
PermitRootLogin prohibit-password  # 禁用密码登录
PasswordAuthentication no          # 只允许密钥
Port 2222                          # 修改 SSH 端口（可选）

# 重启 SSH
systemctl restart sshd
```

### 3. 定期更新

```bash
# 每周更新一次
cd /root/crypto-monitor-bot
./manage.sh update
```

---

## ❓ 常见问题

### Q1: 服务无法启动

```bash
# 查看详细错误
journalctl -u crypto-monitor-bot -n 50

# 常见原因和解决：
# 1. Python 版本太低
python3 --version  # 需要 3.10+

# 2. 依赖未安装
source venv/bin/activate
pip install -r requirements.txt

# 3. .env 配置错误
vim .env  # 检查 Token 和 Chat ID
```

### Q2: 收不到 Telegram 消息

```bash
# 测试 Token
curl -X POST "https://api.telegram.org/bot<你的Token>/getMe"

# 测试发送消息
curl -X POST "https://api.telegram.org/bot<你的Token>/sendMessage" \
  -d "chat_id=<你的ChatID>" \
  -d "text=测试消息"

# 检查日志
./manage.sh logs error
```

### Q3: 内存占用过高

```bash
# 查看内存
./manage.sh status

# 优化方案
vim config/config.yaml
# 减少 symbols_count 到 100
# 增加 data_interval 到 2

# 重启服务
./manage.sh restart
```

### Q4: API 限流频繁

```bash
# 查看限流日志
./manage.sh logs | grep "418"

# 优化配置
vim config/config.yaml

api_rate_limiter:
  base_delay: 0.2      # 增加基础延迟
  max_concurrent: 5    # 减少并发数

# 重启
./manage.sh restart
```

---

## 🎉 部署检查清单

完成后请确认：

- [ ] 服务正常运行 (`systemctl status crypto-monitor-bot`)
- [ ] 日志无错误 (`./manage.sh logs`)
- [ ] 收到 Telegram 启动通知
- [ ] 收到交易信号推送
- [ ] 内存使用 < 1GB
- [ ] CPU 使用 < 50%
- [ ] 开机自启已启用 (`systemctl is-enabled crypto-monitor-bot`)
- [ ] 交互命令正常工作（如果启用 Hermes Agent）

---

## 📞 获取支持

### 查看文档
- [生产环境指南](PRODUCTION.md)
- [快速开始](START.md)
- [完整部署](DEPLOYMENT_GUIDE.md)

### 诊断问题
```bash
./manage.sh diagnose
./manage.sh logs error
```

### 需要帮助？
- GitHub Issues: https://github.com/WEIII2020/crypto-monitor-bot/issues
- 查看日志并提供详细错误信息

---

## ✅ 部署成功！

恭喜！您的 Crypto Monitor Bot 已成功部署到腾讯云。

**下一步**:
1. 观察几小时，确保稳定运行
2. 根据实际情况调整配置
3. 启用 Hermes Agent 获得交互功能
4. 考虑配置数据库进行数据持久化

祝交易愉快！🚀📈
