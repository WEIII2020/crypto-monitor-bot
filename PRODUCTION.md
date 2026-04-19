# 🚀 生产环境部署指南

完整的生产环境部署和监控配置

---

## 📋 部署前检查清单

### 必需配置
- [ ] Telegram Bot Token（TELEGRAM_BOT_TOKEN）
- [ ] Telegram Chat ID（TELEGRAM_CHAT_ID）
- [ ] 服务器 SSH 访问权限
- [ ] Python 3.10+
- [ ] 至少 2GB 内存

### 可选配置
- [ ] Binance API Key（仅交易模式）
- [ ] PostgreSQL 数据库（持久化存储）
- [ ] Redis（缓存加速）

---

## 🏗️ 部署步骤

### 方式 1: 一键部署（推荐）

```bash
# 1. 配置服务器信息
vim deploy.sh
# 修改: SERVER_HOST, SERVER_USER, SERVER_PORT

# 2. 执行部署
./deploy.sh

# 3. 在服务器上配置环境变量
ssh root@your-server
vim /root/crypto-monitor-bot/.env

# 4. 启动服务
systemctl start crypto-monitor-bot
systemctl enable crypto-monitor-bot  # 开机自启
```

### 方式 2: 手动部署

```bash
# 1. 上传代码到服务器
rsync -avz --exclude 'venv' --exclude '.git' \
  ./ root@your-server:/root/crypto-monitor-bot/

# 2. SSH 登录服务器
ssh root@your-server

# 3. 创建虚拟环境
cd /root/crypto-monitor-bot
python3 -m venv venv
source venv/bin/activate

# 4. 安装依赖
pip install -r requirements.txt

# 5. 配置环境变量
cp .env.example .env
vim .env

# 6. 创建 systemd 服务
bash deploy.sh server

# 7. 启动服务
systemctl start crypto-monitor-bot
```

---

## ⚙️ 环境变量配置

### 最小配置（仅信号监控）

```bash
# .env
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
```

### 完整配置（含交易和监控）

```bash
# .env

# Telegram 配置（必需）
export TELEGRAM_BOT_TOKEN="1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
export TELEGRAM_CHAT_ID="123456789"

# Hermes Agent 专用 Token（可选，默认使用 TELEGRAM_BOT_TOKEN）
export HERMES_BOT_TOKEN="your_hermes_bot_token"

# Binance API（仅交易模式需要）
export BINANCE_API_KEY="your_binance_api_key"
export BINANCE_API_SECRET="your_binance_api_secret"

# 数据库配置（可选）
export POSTGRES_HOST="localhost"
export POSTGRES_PORT="5432"
export POSTGRES_USER="crypto_bot"
export POSTGRES_PASSWORD="your_secure_password"
export POSTGRES_DB="crypto_monitor"

# Redis 配置（可选）
export REDIS_HOST="localhost"
export REDIS_PORT="6379"
export REDIS_PASSWORD=""

# 日志级别
export LOG_LEVEL="INFO"
```

---

## 🏥 监控和告警

### 内置健康监控

系统已集成自动健康监控，每 60 秒检查一次：

**监控项目**：
- ✅ **内存使用率**（阈值: 80%）
- ✅ **CPU 使用率**（阈值: 90%）
- ✅ **磁盘空间**（阈值: 85%）
- ✅ **进程状态**（监控进程是否运行）
- ✅ **日志错误率**（阈值: 10 个错误/5分钟）

**告警方式**：
- Telegram 消息推送
- 系统日志记录
- 防重复告警（5 分钟内相同告警只发送一次）

### 手动健康检查

使用 Telegram 命令：
```
/health - 立即运行健康检查
/status - 查看系统状态
```

### 告警配置

编辑阈值（如需调整）：
```python
# src/monitoring/health_monitor.py
self.thresholds = {
    'memory_percent': 80,  # 内存阈值
    'cpu_percent': 90,     # CPU 阈值
    'disk_percent': 85,    # 磁盘阈值
    'error_rate': 10,      # 错误率阈值
    'signal_gap': 600,     # 信号间隔阈值（秒）
}
```

---

## 📊 服务管理

### 使用 systemd（生产环境）

```bash
# 启动服务
systemctl start crypto-monitor-bot

# 停止服务
systemctl stop crypto-monitor-bot

# 重启服务
systemctl restart crypto-monitor-bot

# 查看状态
systemctl status crypto-monitor-bot

# 查看日志
journalctl -u crypto-monitor-bot -f

# 开机自启
systemctl enable crypto-monitor-bot
```

### 使用管理脚本（便捷方式）

```bash
# 启动
./manage.sh start

# 停止
./manage.sh stop

# 重启
./manage.sh restart

# 查看状态
./manage.sh status

# 查看日志
./manage.sh logs          # 普通日志
./manage.sh logs error    # 错误日志
./manage.sh logs follow   # 实时日志
./manage.sh logs signal   # 信号日志

# 系统诊断
./manage.sh diagnose

# 更新代码
./manage.sh update

# 清理日志
./manage.sh clean
```

---

## 🎛️ 运行模式

### 1. 监控模式（monitor）
只采集数据，不生成信号
```bash
systemctl start crypto-monitor-bot  # 默认 signal 模式
# 修改 /etc/systemd/system/crypto-monitor-bot.service
# ExecStart=.../main_phase2.py --mode monitor
```

### 2. 信号模式（signal）- 推荐
采集数据 + 生成信号 + Telegram 推送
```bash
# 默认模式，无需修改
```

### 3. 统一模式（unified）
信号模式 + Hermes Agent 交互
```bash
# 使用带监控的启动脚本
./run_with_monitoring.sh signal
```

### 4. 交易模式（trade）
完整功能：监控 + 信号 + 自动交易
```bash
# 修改 systemd 服务
ExecStart=.../main_phase2.py --mode trade
```

---

## 🔍 日志管理

### 日志位置
```
logs/
├── bot.log          # 主日志
├── bot.error.log    # 错误日志
└── monitor.log      # 监控进程日志
```

### 日志轮转配置

创建 `/etc/logrotate.d/crypto-monitor-bot`:
```
/root/crypto-monitor-bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 root root
    sharedscripts
    postrotate
        systemctl reload crypto-monitor-bot > /dev/null 2>&1 || true
    endscript
}
```

---

## 🔐 安全建议

### 1. 保护敏感信息
```bash
# .env 文件权限
chmod 600 .env

# 避免将 .env 提交到 git
echo ".env" >> .gitignore
```

### 2. 使用专用 Bot Token
- 为生产环境创建独立的 Telegram Bot
- 不要共享 Bot Token
- 定期更换密钥

### 3. 限制 SSH 访问
```bash
# 禁用密码登录，只允许密钥
vim /etc/ssh/sshd_config
# PasswordAuthentication no
```

### 4. 防火墙配置
```bash
# 只开放必要端口
ufw allow 22/tcp   # SSH
ufw enable
```

---

## 📈 性能优化

### 内存优化
```yaml
# config/config.yaml

# 减少监控币种数量
symbols_count: 100  # 从 200 降低

# 调整历史数据长度
history_length: 180  # 从 360 降低（减少内存占用）
```

### CPU 优化
```yaml
# config/config.yaml

# 调整数据采集频率
data_interval: 2  # 从 1 秒改为 2 秒

# 减少并发请求
max_concurrent_requests: 5  # 从 8 降低
```

### API 限流优化
```yaml
# config/config.yaml

api_rate_limiter:
  max_concurrent: 8      # 并发请求数
  base_delay: 0.1        # 基础延迟（秒）
  max_delay: 2.0         # 最大延迟
  backoff_factor: 2      # 退避因子
```

---

## 🆘 故障排查

### 问题 1: 服务无法启动
```bash
# 检查日志
journalctl -u crypto-monitor-bot -n 50

# 常见原因
# - Python 版本不兼容（需要 3.10+）
# - 依赖未安装
# - .env 配置错误

# 解决方法
pip install -r requirements.txt
vim .env  # 检查配置
```

### 问题 2: 内存占用过高
```bash
# 查看内存使用
./manage.sh status

# 解决方法
# 1. 减少监控币种数量
# 2. 调整历史数据长度
# 3. 增加服务器内存
```

### 问题 3: API 限流频繁
```bash
# 查看限流日志
./manage.sh logs | grep "418"

# 解决方法
# 1. 增加 base_delay
# 2. 减少并发请求
# 3. 减少监控币种
```

### 问题 4: Telegram 消息发送失败
```bash
# 检查 Token 和 Chat ID
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_CHAT_ID

# 测试连接
curl -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
```

---

## 📞 获取支持

### 查看文档
- [快速开始](START.md)
- [部署指南](DEPLOYMENT_GUIDE.md)
- [架构分析](ARCHITECTURE_ANALYSIS.md)

### 日志诊断
```bash
# 运行完整诊断
./manage.sh diagnose

# 查看最近错误
./manage.sh logs error 100
```

### 提交问题
如遇到问题，请提供：
1. 错误日志（`./manage.sh logs error`）
2. 系统状态（`./manage.sh status`）
3. 配置文件（隐藏敏感信息）

---

## ✅ 部署检查清单

部署完成后，请确认：

- [ ] 服务正常运行（`systemctl status crypto-monitor-bot`）
- [ ] 日志无严重错误（`./manage.sh logs`）
- [ ] Telegram 接收到启动通知
- [ ] 健康监控正常工作（`/health` 命令）
- [ ] 信号正常生成（查看日志或 Telegram）
- [ ] 内存使用正常（< 1GB）
- [ ] CPU 使用正常（< 50%）
- [ ] 开机自启已启用（`systemctl is-enabled crypto-monitor-bot`）

---

## 🎉 完成

恭喜！您的 Crypto Monitor Bot 已成功部署到生产环境。

**下一步**：
- 使用 `/help` 查看 Telegram 命令
- 监控系统健康状态
- 根据实际情况调整配置

祝交易愉快！🚀
