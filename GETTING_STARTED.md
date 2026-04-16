# 🚀 快速开始指南

10分钟完成安装配置，开始监控加密货币市场！

---

## 📋 前置要求

### 必需

- ✅ Python 3.9+ 
- ✅ Redis（用于缓存）
- ✅ PostgreSQL（用于历史数据）
- ✅ Telegram Bot Token

### 推荐

- 💻 2核CPU, 2GB RAM
- 🌐 稳定的网络连接
- ⏰ 24/7运行环境（VPS/服务器）

---

## ⚡ 快速安装（3步）

### Step 1: 克隆项目

```bash
git clone <your-repo-url>
cd crypto-monitor-bot
```

### Step 2: 安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### Step 3: 配置环境

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置（填入你的API密钥）
nano .env  # 或使用你喜欢的编辑器
```

---

## ⚙️ 配置说明

### 1. Telegram Bot配置

**获取Bot Token:**
1. 在Telegram中搜索 `@BotFather`
2. 发送 `/newbot` 创建新机器人
3. 按提示完成，获得Token
4. 复制Token到 `.env` 文件

**获取Chat ID:**
```bash
# 方法1: 使用测试脚本
python test_telegram.py

# 方法2: 手动获取
# 1. 给你的bot发送一条消息
# 2. 访问: https://api.telegram.org/bot<YourBOTToken>/getUpdates
# 3. 找到 "chat":{"id":123456}
```

### 2. 数据库配置

**Redis:**
```bash
# 启动Redis（本地）
redis-server

# 或使用Docker
docker run -d -p 6379:6379 redis:alpine
```

**PostgreSQL:**
```bash
# 创建数据库
createdb crypto_monitor

# 或使用Docker
docker run -d \
  -e POSTGRES_DB=crypto_monitor \
  -e POSTGRES_PASSWORD=yourpassword \
  -p 5432:5432 \
  postgres:14-alpine
```

### 3. .env 文件示例

```bash
# Telegram配置
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=987654321

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# PostgreSQL配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=crypto_monitor
POSTGRES_USER=postgres
POSTGRES_PASSWORD=yourpassword

# 监控配置（可选）
MAX_SYMBOLS=50
CHECK_INTERVAL=30
```

---

## 🎯 启动Bot

### 方式1: 直接运行（推荐新手）

```bash
# 启动（被动监控模式）
python main.py

# 你会看到：
# 🚀 Starting Crypto Monitor Bot...
# ✅ Database connections established
# ✅ Selected 50 symbols
# ✅ Subscribed to 50 symbols
# ✅ Bot is running!
```

### 方式2: 使用妖币策略（有经验者）

```bash
# 1. 启用策略（编辑 config.yaml）
pump_dump_strategy:
  enabled: true  # 改为true

# 2. 启动集成版
python main_with_pump_dump.py
```

⚠️ **警告:** 妖币策略是主动交易策略，有风险！建议先阅读 [docs/strategies/pump-dump-trading.md](docs/strategies/pump-dump-trading.md)

---

## ✅ 验证安装

### 1. 检查日志

```bash
# 查看实时日志
tail -f logs/crypto_monitor.log

# 应该看到：
# [INFO] Connected to Binance WebSocket
# [INFO] Subscribed to BTC/USDT
# [INFO] Processed BTC/USDT: $45,123.45
```

### 2. 测试Telegram通知

```bash
# 运行测试脚本
python test_telegram.py

# 你应该在Telegram收到测试消息
```

### 3. 检查数据库连接

```bash
# Redis
redis-cli ping
# 应该返回: PONG

# PostgreSQL
psql -d crypto_monitor -c "SELECT 1"
# 应该返回: 1
```

---

## 📊 第一个告警

**预期时间:** 5-30分钟

启动后，你会在5-30分钟内收到第一个告警：

```
🟡 价格波动告警
📈 BTC/USDT
💰 价格: $45,123.45
📊 涨跌: +8.5%
⏰ 时间: 14:30
```

**为什么需要等待？**
- 系统需要累积历史数据
- 多时间框架分析需要30分钟数据
- 确认信号需要连续观察

---

## 🎯 下一步

恭喜！你的监控系统已经运行了。

### 新手路径

1. ✅ 观察告警（1-2天）
2. 📖 阅读 [docs/user-guide/alerts.md](docs/user-guide/alerts.md) 理解告警类型
3. ⚙️ 调整 `config.yaml` 参数
4. 🎓 学习 [docs/strategies/rave-analysis.md](docs/strategies/rave-analysis.md) 深入理解

### 进阶路径

1. ✅ 启用妖币策略
2. 📝 纸面交易1-2周
3. 💰 小资金实盘
4. 🚀 逐步扩大

---

## 🐛 常见问题

### Q: Redis连接失败？

```bash
# 检查Redis是否运行
redis-cli ping

# 如果没有运行
redis-server  # 前台运行
# 或
redis-server --daemonize yes  # 后台运行
```

### Q: Telegram不发送消息？

```bash
# 1. 检查Token和Chat ID
python test_telegram.py

# 2. 确保你给bot发送过消息
# 3. 检查bot没有被你屏蔽
```

### Q: 没有收到告警？

**可能原因:**
1. 系统刚启动（等待5-30分钟）
2. 市场波动较小（正常）
3. 阈值设置过高（调整 `config.yaml`）

### Q: CPU/内存占用过高？

```bash
# 减少监控币种数量（config.yaml）
symbols:
  max_count: 30  # 从50改为30
```

更多问题查看: [docs/user-guide/faq.md](docs/user-guide/faq.md)

---

## 🔧 配置调整

### 减少告警（降低噪音）

```yaml
# config.yaml
volatility:
  warning_threshold: 15.0  # 从10.0改为15.0
  
whale_detection:
  volume_spike_threshold: 7.0  # 从5.0改为7.0
```

### 增加告警（更灵敏）

```yaml
# config.yaml
volatility:
  warning_threshold: 5.0  # 从10.0改为5.0
  
whale_detection:
  volume_spike_threshold: 3.0  # 从5.0改为3.0
```

完整配置说明: [docs/user-guide/configuration.md](docs/user-guide/configuration.md)

---

## 📚 推荐阅读顺序

1. ✅ **你在这里** → GETTING_STARTED.md
2. 📖 [docs/user-guide/features.md](docs/user-guide/features.md) - 了解所有功能
3. 📋 [docs/user-guide/alerts.md](docs/user-guide/alerts.md) - 理解告警类型
4. 🎯 [docs/strategies/rave-analysis.md](docs/strategies/rave-analysis.md) - 深度分析
5. ⚡ [docs/strategies/pump-dump-trading.md](docs/strategies/pump-dump-trading.md) - 主动策略

---

## 🎊 恭喜！

你已经成功启动了Crypto Monitor Bot！

**现在你可以:**
- ✅ 实时监控50个加密货币
- ✅ 接收Telegram告警
- ✅ 识别巨鲸活动
- ✅ 发现庄家操控

**记住:**
- 💪 这是一个工具，不是印钞机
- 📚 持续学习，理解策略
- 🎯 严格纪律，控制风险

祝交易顺利！🚀

---

**需要帮助？** 查看 [docs/user-guide/faq.md](docs/user-guide/faq.md) 或提交Issue

**最后更新:** 2026-04-14
