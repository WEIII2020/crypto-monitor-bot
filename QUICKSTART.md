# 🚀 加密货币监控机器人 - 快速启动指南

## 📋 前置要求

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Telegram Bot Token

## ⚡ 5 分钟快速启动

### 1️⃣ 安装依赖

```bash
cd crypto-monitor-bot
pip install -r requirements.txt
```

### 2️⃣ 创建 Telegram Bot

1. 在 Telegram 中找到 [@BotFather](https://t.me/botfather)
2. 发送 `/newbot` 创建机器人
3. 获取你的 Bot Token（格式：`1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`）
4. 发送 `/start` 给你的新机器人
5. 获取你的 Chat ID：
   - 访问 `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
   - 找到 `"chat":{"id": 123456789}` 中的数字

### 3️⃣ 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

**最小必填配置：**

```bash
# Telegram（必填）
TELEGRAM_BOT_TOKEN=你的机器人token
TELEGRAM_CHAT_ID=你的chat_id

# 数据库（如果使用本地）
DATABASE_URL=postgresql://cryptobot:password@localhost:5432/crypto_monitor
REDIS_URL=redis://:password@localhost:6379/0

# 告警阈值（可选，默认值）
WARNING_THRESHOLD_5M=10.0    # 10% 触发警告
CRITICAL_THRESHOLD_5M=20.0   # 20% 触发严重告警
```

### 4️⃣ 初始化数据库

```bash
# 启动 PostgreSQL 和 Redis（如果使用 Docker）
docker-compose up -d postgres redis

# 或者使用本地安装
# 确保 PostgreSQL 和 Redis 正在运行

# 初始化数据库表
python scripts/setup_db.py
```

### 5️⃣ 启动监控机器人

```bash
python main.py
```

**期望输出：**

```
2026-04-12 10:30:00 | INFO     | __main__:start:35 - 🚀 Starting Crypto Monitor Bot...
2026-04-12 10:30:01 | INFO     | __main__:start:40 - ✅ Database connections established
2026-04-12 10:30:02 | INFO     | base_collector:connect_with_retry:24 - binance connected successfully
2026-04-12 10:30:02 | INFO     | __main__:start:49 - ✅ Subscribed to 5 symbols
2026-04-12 10:30:02 | INFO     | __main__:start:58 - ✅ Bot is running! Press Ctrl+C to stop.
```

## 📱 接收告警

机器人会在以下情况发送 Telegram 通知：

- **⚠️ 警告（10%）**：5 分钟内价格波动 ≥ 10%
- **🚨 严重（20%）**：5 分钟内价格波动 ≥ 20%

**告警消息格式：**

```
🚨 CRITICAL ALERT

📈 BTC/USDT on BINANCE

💰 Current Price: $67,543.21
📊 Change: +23.45% (5 min)

⏰ Time: 2026-04-12 10:35:00
```

## 🎯 监控的币种

默认监控（可在 `main.py` 中修改）：

- BTC/USDT（比特币）
- ETH/USDT（以太坊）
- BNB/USDT（币安币）
- SOL/USDT（Solana）
- XRP/USDT（瑞波币）

**添加更多币种：**

编辑 `main.py` 第 26-32 行：

```python
self.symbols = [
    'BTC/USDT',
    'ETH/USDT',
    # 添加你想监控的币种
    'DOGE/USDT',
    'SHIB/USDT',
]
```

## 🛠️ 常见问题

### Q: 如何停止机器人？

A: 按 `Ctrl+C` 优雅关闭。

### Q: 数据库连接失败？

A: 检查 PostgreSQL 和 Redis 是否运行：

```bash
# PostgreSQL
psql -h localhost -U cryptobot -d crypto_monitor

# Redis
redis-cli ping
```

### Q: Telegram 通知收不到？

A: 检查以下几点：

1. Bot Token 是否正确
2. Chat ID 是否正确（必须是数字）
3. 是否已经给机器人发送过 `/start`

### Q: 如何调整告警阈值？

A: 编辑 `.env` 文件中的阈值：

```bash
WARNING_THRESHOLD_5M=15.0    # 改为 15%
CRITICAL_THRESHOLD_5M=25.0   # 改为 25%
```

重启机器人生效。

## 🐳 Docker 快速启动（推荐）

如果你想要一键启动所有服务：

```bash
# 创建 docker-compose.yml（示例）
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: cryptobot
      POSTGRES_PASSWORD: password
      POSTGRES_DB: crypto_monitor
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass password
    ports:
      - "6379:6379"

volumes:
  postgres_data:
EOF

# 启动所有服务
docker-compose up -d

# 等待 5 秒让数据库启动
sleep 5

# 初始化数据库
python scripts/setup_db.py

# 启动机器人
python main.py
```

## 📊 查看日志

日志文件保存在 `logs/` 目录：

```bash
# 查看今天的日志
tail -f logs/crypto_monitor_$(date +%Y-%m-%d).log

# 搜索告警记录
grep "Alert sent" logs/*.log
```

## 🔧 高级配置

### 夜间模式（可选）

在 `.env` 中启用夜间模式，避免深夜打扰：

```bash
ENABLE_NIGHT_MODE=true
NIGHT_START_HOUR=23    # 晚上 11 点开始
NIGHT_END_HOUR=7       # 早上 7 点结束
```

### 音量异常检测（可选）

```bash
VOLUME_WARNING_MULTIPLIER=5.0    # 音量是平均值的 5 倍
VOLUME_CRITICAL_MULTIPLIER=10.0  # 音量是平均值的 10 倍
```

## 🎉 完成！

现在你的加密货币监控机器人已经在运行了！

**接下来可以做什么？**

- 📈 添加更多交易所（OKX、Gate.io）
- 🤖 实现庄家行为识别
- 📊 创建 Web 仪表盘
- 🔍 添加套利机会检测

## 📞 获取帮助

如果遇到问题：

1. 查看日志文件 `logs/crypto_monitor_*.log`
2. 检查数据库连接
3. 确认 Telegram 配置正确
4. 查看项目 README.md

**祝你交易顺利！** 🚀
