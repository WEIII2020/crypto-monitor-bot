# 🤖 Crypto Monitor Bot - Hermes Agent 学习指南

> **文档目的：** 让 Hermes Agent 完整理解 crypto-monitor-bot 的架构、工作流程和优化策略，实现智能化监控和交易决策。

---

## 📋 目录

1. [系统概述](#系统概述)
2. [核心架构](#核心架构)
3. [监控策略](#监控策略)
4. [信号融合系统](#信号融合系统)
5. [部署配置](#部署配置)
6. [性能优化](#性能优化)
7. [API接口](#api接口)
8. [Hermes集成方案](#hermes集成方案)

---

## 系统概述

### 🎯 核心功能

**Crypto Monitor Bot** 是一个实时加密货币监控系统，基于 **Lana方法** 和 **朋友的妖币方法**：

```
实时监控 → 多维度分析 → 信号融合 → Telegram告警 → Hermes执行
```

### 📊 当前状态

| 指标 | 数值 |
|------|------|
| 监控币种 | **167个** USDT交易对 |
| 监控频率 | 价格:30s, 巨鲸:60s, OI:120s |
| 告警阈值 | WARNING:15%, CRITICAL:25% |
| 部署位置 | 腾讯云 (119.28.43.237) |
| 运行时长 | 24/7 持续运行 |
| 数据存储 | PostgreSQL + Redis |

---

## 核心架构

### 系统组件

```
┌─────────────────────────────────────────┐
│         Binance WebSocket API            │
│    (实时价格 + 成交量 + OI数据)            │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│        BinanceCollector (采集器)         │
│  • 50个币种 WebSocket订阅                 │
│  • 实时价格流                             │
│  • 存入Redis（时序数据）                   │
└──────────────┬──────────────────────────┘
               ↓
       ┌───────┴───────┐
       ↓               ↓
┌─────────────┐  ┌─────────────┐
│   Redis     │  │  PostgreSQL │
│  (缓存层)    │  │  (持久层)    │
└──────┬──────┘  └──────┬──────┘
       │                │
       ↓                ↓
┌─────────────────────────────────────────┐
│           分析器层 (Analyzers)            │
│                                          │
│  1️⃣ VolatilityDetector (30s)            │
│     • 5分钟价格波动检测                   │
│     • WARNING: 15%, CRITICAL: 25%        │
│                                          │
│  2️⃣ WhaleDetectorV2 (60s)               │
│     • 巨鲸交易行为识别                     │
│     • 成交量5倍异常检测                    │
│                                          │
│  3️⃣ PumpDumpDetector (智能频率)          │
│     • 6小时涨幅>20%                       │
│     • 弃盘点检测(买卖比<45%)               │
│     • 朋友的妖币方法                       │
│                                          │
│  4️⃣ OIMonitor (120s) - Lana核心         │
│     • 48h OI变动>60%                     │
│     • 价格变动<3% (资金埋伏)               │
│                                          │
│  5️⃣ SquareMonitor (框架就绪)             │
│     • 币安广场热度追踪                     │
│     • 散户情绪指标                        │
│                                          │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│      SignalFusion (信号融合器)            │
│                                          │
│  评分权重 (Lana方法):                     │
│  • OI异常:      40分 ← 最重要             │
│  • 价格波动:    30分                      │
│  • 巨鲸行为:    20分                      │
│  • 广场热度:    10分                      │
│  • 暴涨检测:    30分 (朋友方法)            │
│                                          │
│  黄金组合加成:                            │
│  • OI+价格:     +15分                    │
│  • OI+广场:     +10分                    │
│  • 暴涨+OI:     +20分                    │
│                                          │
│  行动阈值:                               │
│  • ≥65分 = WATCH (观察)                  │
│  • ≥85分 = BUY   (买入信号)              │
│                                          │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│      TelegramNotifier (告警输出)          │
│  • 单一信号告警                           │
│  • 融合信号告警                           │
│  • 时间格式: 2026-04-16 19:39:22         │
└──────────────┬──────────────────────────┘
               ↓
         [Telegram Bot]
               ↓
         [您 & Hermes Agent]
```

---

## 监控策略

### 币种筛选逻辑

**文件位置:** `src/utils/symbol_selector.py`

```python
# 当前筛选条件 (2026-04-16 优化后)
{
    'min_volume_usd': 1_000_000,      # $1M 最小日成交量
    'max_volume_usd': 500_000_000,    # $500M 最大 (包含主流币)
    'min_price': 0.01,                # $0.01 最低价格
    'max_price': 10.0,                # $10 最高价格
    'max_symbols': 200                # 最多200个币种
}
```

**筛选流程:**
1. 获取Binance全部交易对 (3562个)
2. 过滤USDT交易对
3. 排除稳定币、法币、杠杆代币
4. 应用成交量和价格过滤
5. 按成交量排序，取前167个

### 告警参数配置

**文件位置:** `src/config.py`

| 参数 | 值 | 说明 |
|------|-----|------|
| WARNING_THRESHOLD_5M | 15.0% | 5分钟价格波动警告线 |
| CRITICAL_THRESHOLD_5M | 25.0% | 5分钟价格波动严重线 |
| 告警冷却时间 | 600秒 | 同一币种10分钟内不重复 |

**优化历史:**
- 2026-04-15: 10% → 15% (降低误报)
- 2026-04-16: 20% → 25% (只关注大波动)

---

## 信号融合系统

### Lana方法核心逻辑

**文件位置:** `src/analyzers/signal_fusion.py`

#### 评分机制

```python
weights = {
    'OI_SPIKE': 40,         # OI异常 - Lana核心
    'PRICE_SPIKE': 30,      # 价格突变
    'WHALE_ACTIVITY': 20,   # 巨鲸活动
    'SQUARE_TRENDING': 10,  # 广场热度
    'PUMP_DETECTED': 30     # 暴涨检测 (朋友方法)
}
```

#### 黄金组合

```python
# 组合1: OI异常 + 价格波动 = +15分
if 'OI_SPIKE' in signals and 'PRICE_SPIKE' in signals:
    bonus += 15
    # 解读: 资金埋伏 + 价格启动 = 高确定性

# 组合2: OI异常 + 广场热度 = +10分  
if 'OI_SPIKE' in signals and 'SQUARE_TRENDING' in signals:
    bonus += 10
    # 解读: 资金埋伏 + 散户进场 = 即将拉盘

# 组合3: 暴涨 + OI异常 = +20分
if 'PUMP_DETECTED' in signals and 'OI_SPIKE' in signals:
    bonus += 20
    # 解读: 已暴涨 + 资金提前埋伏 = 超高确定性
```

#### 行动建议

```
总分 < 65分  → IGNORE (不发告警)
总分 65-84分 → WATCH  (观察，密切关注)
总分 ≥85分   → BUY    (买入信号确认)
```

### 告警消息格式

#### 单一信号告警
```
⚠️ WARNING ALERT

📈 BTC/USDT on BINANCE

💰 Current Price: $60,000.00
📊 Change: +16.50% (5 min)

⏰ Time: 2026-04-16 19:39:22
```

#### 融合信号告警 (重点关注)
```
🟢 综合信号 - BUY

🪙 BTC/USDT
💰 现价: $60,000.0000

📊 综合评分: 90/100

🔍 触发信号 (3个):
  • OI_SPIKE: 40分
  • PRICE_SPIKE: 30分
  • SQUARE_TRENDING: 10分

⚡ 组合加成: +10分

🎯 建议行动: BUY

✅ 买入信号确认:
  • 多个信号同时触发
  • 综合评分达到90分
  • 建议：轻仓试探
  • 止损：严格执行（lana规则：亏200u出）

⚠️ lana方法:
  • 规则执行 > 主观判断
  • 亏200u立即止损
  • 只做一个方向，不做反向
```

---

## 部署配置

### 服务器信息

```
服务器: 腾讯云 Lighthouse
IP: 119.28.43.237
系统: Ubuntu 20.04
进程管理: Supervisor
数据库: PostgreSQL 16 + Redis 7
```

### 目录结构

```
/opt/crypto-monitor-bot/
├── main.py                          # 主程序入口
├── requirements.txt                 # Python依赖
├── .env                            # 环境变量配置
├── venv/                           # Python虚拟环境
└── src/
    ├── config.py                   # 配置管理
    ├── collectors/                 # 数据采集器
    │   ├── base_collector.py
    │   └── binance_collector.py    # Binance WebSocket
    ├── analyzers/                  # 分析器
    │   ├── volatility_detector.py  # 价格波动
    │   ├── whale_detector_v2.py    # 巨鲸检测
    │   ├── pump_dump_detector.py   # 暴涨暴跌
    │   ├── oi_monitor.py          # OI监控 (Lana)
    │   ├── square_monitor.py      # 广场热度 (Lana)
    │   └── signal_fusion.py       # 信号融合 (Lana)
    ├── database/                   # 数据库
    │   ├── postgres.py            # PostgreSQL客户端
    │   └── redis_client.py        # Redis客户端
    ├── notifiers/                  # 通知模块
    │   └── telegram_notifier.py   # Telegram Bot
    └── utils/                      # 工具类
        ├── logger.py              # 日志系统
        ├── symbol_selector.py     # 币种筛选
        └── performance_monitor.py # 性能监控
```

### 环境变量 (.env)

```bash
# Telegram配置
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# 数据库配置
DATABASE_URL=postgresql://cryptobot:P%40ssw0rd2024%21Crypto%23DB@localhost:5432/crypto_monitor
REDIS_URL=redis://:R3dis%24Secure%232024Pass%21@localhost:6379/0

# 告警阈值
WARNING_THRESHOLD_5M=15.0
CRITICAL_THRESHOLD_5M=25.0

# 币安API (可选)
BINANCE_API_KEY=
BINANCE_API_SECRET=
```

### Supervisor配置

```ini
[program:crypto-monitor-bot]
command=/opt/crypto-monitor-bot/venv/bin/python3 main.py
directory=/opt/crypto-monitor-bot
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/crypto-monitor-bot.log
environment=PATH="/opt/crypto-monitor-bot/venv/bin"
```

---

## 性能优化

### 已完成的优化 (2026-04-16)

#### 1. Bug修复
- ✅ 时间格式：`64915.xxx` → `2026-04-16 19:39:22`
- ✅ Redis decode错误修复 (添加get/set方法)

#### 2. 参数优化 (降低误报)

| 参数 | 优化前 | 优化后 | 效果 |
|------|--------|--------|------|
| WARNING阈值 | 10% | 15% | 减少40%误报 |
| CRITICAL阈值 | 20% | 25% | 只关注大波动 |
| 告警冷却 | 5分钟 | 10分钟 | 避免重复告警 |
| OI突变阈值 | 50% | 60% | 更严格 |
| 价格不动阈值 | <5% | <3% | 更精确 |
| WATCH分数 | 60分 | 65分 | 提高门槛 |
| BUY分数 | 80分 | 85分 | 更谨慎 |

#### 3. 监控范围扩展

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 币种数量 | 50个 | 167个 |
| 最小成交量 | $5M | $1M |
| 最大成交量 | $50M | $500M |

#### 4. 预期效果

**优化前：**
- 告警频率：5-10次/小时
- 误报率：40-50%

**优化后：**
- 告警频率：2-3次/小时 ⬇️ 60%
- 误报率：20-30% ⬇️ 50%

---

## API接口

### 数据库表结构

#### alerts表 (告警记录)

```sql
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    symbol_id INTEGER REFERENCES symbols(id),
    exchange VARCHAR(50) NOT NULL,
    alert_type VARCHAR(50) NOT NULL,    -- PRICE_SPIKE, OI_SPIKE, SIGNAL_FUSION等
    alert_level VARCHAR(20) NOT NULL,   -- INFO, WARNING, CRITICAL
    price DECIMAL(20, 8),
    change_percent DECIMAL(10, 4),
    message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### symbols表 (币种信息)

```sql
CREATE TABLE symbols (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) UNIQUE NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    base_currency VARCHAR(10),
    quote_currency VARCHAR(10),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Redis数据结构

```
# 价格时序数据 (Sorted Set)
price:binance:BTC/USDT:1m
  → {价格数据JSON}: timestamp

# 告警去重标记 (String with TTL)
alert:sent:BTC/USDT:PRICE_SPIKE
  → "1" (TTL: 600秒)

# WebSocket连接状态
ws:status:binance
  → "connected" | "disconnected"

# OI历史数据 (String with TTL)
oi:BTC/USDT:48h
  → "12345678.90" (TTL: 48小时)
```

### 查询示例

#### 获取最近告警

```sql
SELECT 
    a.alert_type,
    s.symbol,
    a.alert_level,
    a.change_percent,
    a.created_at
FROM alerts a
JOIN symbols s ON a.symbol_id = s.id
WHERE a.created_at > NOW() - INTERVAL '24 hours'
ORDER BY a.created_at DESC
LIMIT 50;
```

#### 统计告警类型分布

```sql
SELECT 
    alert_type,
    COUNT(*) as count,
    AVG(change_percent) as avg_change
FROM alerts
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY alert_type
ORDER BY count DESC;
```

---

## Hermes集成方案

### 集成架构

```
┌─────────────────────────────────────────┐
│         Hermes Agent Bot                 │
│                                          │
│  📱 Telegram命令处理                     │
│  ├─ /monitor_status                     │
│  ├─ /monitor_stats                      │
│  ├─ /optimize_monitor                   │
│  ├─ /adjust_threshold                   │
│  └─ /auto_trade                         │
│                                          │
│  🧠 决策引擎                             │
│  ├─ 读取crypto-monitor-bot数据          │
│  ├─ 分析信号质量                         │
│  ├─ 执行交易决策                         │
│  └─ 反馈优化建议                         │
│                                          │
└──────────────┬──────────────────────────┘
               │
               ↓ (共享PostgreSQL + Redis)
               │
┌──────────────┴──────────────────────────┐
│      Crypto Monitor Bot (监控层)         │
│  • 实时监控167个币种                      │
│  • 信号融合 (Lana方法)                   │
│  • Telegram告警输出                      │
└─────────────────────────────────────────┘
```

### 推荐的Hermes命令

#### 1. 监控状态查询

```python
@bot.command("monitor_status")
async def monitor_status(update, context):
    """查看crypto-monitor-bot运行状态"""
    
    # 检查服务状态
    status = check_service_status()
    
    # 查询数据库连接
    db_status = check_db_connections()
    
    # 查询最近告警
    recent_alerts = get_recent_alerts(minutes=60)
    
    message = f"""
📊 Monitor Bot 状态

🟢 服务状态: {status}
💾 数据库: {db_status}
📈 监控币种: 167个
⏱️ 运行时间: {uptime}

📢 最近1小时告警: {len(recent_alerts)}条
    """
    
    await update.message.reply_text(message)
```

#### 2. 告警统计分析

```python
@bot.command("monitor_stats")
async def monitor_stats(update, context):
    """分析告警质量和统计"""
    
    stats = analyze_alert_stats(hours=24)
    
    message = f"""
📊 过去24小时统计

🔔 告警总数: {stats['total']}
✅ 有效信号: {stats['valid']} ({stats['valid_rate']}%)
❌ 误报: {stats['false_positive']} ({stats['fp_rate']}%)

📈 按类型分布:
  • PRICE_SPIKE: {stats['price_spike']}
  • OI_SPIKE: {stats['oi_spike']}
  • WHALE_ACTIVITY: {stats['whale']}
  • SIGNAL_FUSION: {stats['fusion']}

🎯 高分信号 (≥85分): {stats['high_score']}
    """
    
    await update.message.reply_text(message)
```

#### 3. 智能优化建议

```python
@bot.command("optimize_monitor")
async def optimize_monitor(update, context):
    """基于历史数据优化参数"""
    
    # 1. 分析过去7天数据
    analysis = analyze_performance(days=7)
    
    # 2. 计算最优参数
    recommendations = calculate_optimal_params(analysis)
    
    # 3. 生成建议
    message = f"""
🤖 智能优化建议

📊 分析周期: 过去7天
🔔 总告警: {analysis['total_alerts']}
✅ 有效率: {analysis['accuracy']}%

💡 优化建议:
"""
    
    if analysis['false_positive_rate'] > 30:
        message += f"\n  • WARNING阈值建议: {recommendations['warning_threshold']}%"
        message += f"\n  • CRITICAL阈值建议: {recommendations['critical_threshold']}%"
    
    if analysis['missed_opportunities'] > 10:
        message += f"\n  • 建议降低阈值，当前可能错过机会"
    
    message += f"\n\n❓ 是否应用这些优化？"
    message += f"\n回复 /apply_optimization 确认执行"
    
    await update.message.reply_text(message)
```

#### 4. 自动交易决策

```python
@bot.command("auto_trade")
async def auto_trade(update, context):
    """基于融合信号自动交易"""
    
    # 1. 获取最新融合信号
    fusion_signals = get_fusion_signals(minutes=10)
    
    # 2. 过滤高分信号
    high_score_signals = [s for s in fusion_signals if s['score'] >= 85]
    
    if not high_score_signals:
        await update.message.reply_text("暂无高分信号")
        return
    
    # 3. 执行交易决策
    for signal in high_score_signals:
        # Lana规则检查
        if check_lana_rules(signal):
            # 计算仓位
            position_size = calculate_position(signal['score'])
            
            # 执行下单
            order = execute_trade(
                symbol=signal['symbol'],
                action=signal['action'],  # BUY
                size=position_size,
                stop_loss=200  # Lana规则：亏200u出
            )
            
            message = f"""
✅ 自动交易执行

🪙 币种: {signal['symbol']}
📊 信号分数: {signal['score']}/100
💰 开仓价格: ${order['price']}
📦 仓位: {position_size} USDT
🛑 止损: 200 USDT

📋 信号详情:
{format_signal_details(signal)}
            """
            
            await update.message.reply_text(message)
```

### 数据共享方式

#### 方案1: 共享数据库 (推荐)

```python
# Hermes Agent直接读取PostgreSQL
from sqlalchemy import create_engine

engine = create_engine('postgresql://cryptobot:password@localhost:5432/crypto_monitor')

# 查询最新融合信号
query = """
SELECT 
    s.symbol,
    a.alert_type,
    a.message,
    a.created_at
FROM alerts a
JOIN symbols s ON a.symbol_id = s.id
WHERE a.alert_type = 'SIGNAL_FUSION'
  AND a.created_at > NOW() - INTERVAL '10 minutes'
ORDER BY a.created_at DESC;
"""
```

#### 方案2: Redis订阅 (实时)

```python
# Hermes Agent订阅Redis频道
import redis

r = redis.Redis(host='localhost', port=6379, db=0)
pubsub = r.pubsub()
pubsub.subscribe('crypto_alerts')

for message in pubsub.listen():
    if message['type'] == 'message':
        alert = json.loads(message['data'])
        if alert['score'] >= 85:
            # 触发交易逻辑
            execute_trading_strategy(alert)
```

#### 方案3: API接口 (未来)

```python
# crypto-monitor-bot添加HTTP API
# Hermes Agent通过HTTP查询

import aiohttp

async with aiohttp.ClientSession() as session:
    async with session.get('http://localhost:8000/api/signals/latest') as resp:
        signals = await resp.json()
```

---

## 关键文件清单

### 必读文件

1. **README.md** - 项目介绍
2. **SYSTEM_OVERVIEW.md** - 系统架构详解
3. **LANA_UPGRADE.md** - Lana方法实现细节
4. **OPTIMIZATION_CONFIG.md** - 当前优化配置
5. **本文档** - Hermes集成指南

### 配置文件

1. **.env** - 环境变量（包含敏感信息）
2. **src/config.py** - 配置管理代码
3. **requirements.txt** - Python依赖

### 核心代码

1. **main.py** - 程序入口
2. **src/analyzers/signal_fusion.py** - 信号融合逻辑
3. **src/analyzers/oi_monitor.py** - OI监控 (Lana核心)
4. **src/utils/symbol_selector.py** - 币种筛选

---

## 快速命令参考

### 服务管理

```bash
# 查看服务状态
supervisorctl status crypto-monitor-bot

# 重启服务
supervisorctl restart crypto-monitor-bot

# 查看日志
tail -f /var/log/crypto-monitor-bot.log

# 查看最近告警
tail -n 100 /var/log/crypto-monitor-bot.log | grep "Alert sent"
```

### 数据库查询

```bash
# 连接PostgreSQL
psql -U cryptobot -d crypto_monitor

# 查看最近告警
SELECT * FROM alerts ORDER BY created_at DESC LIMIT 10;

# 统计告警类型
SELECT alert_type, COUNT(*) FROM alerts 
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY alert_type;
```

### Redis查询

```bash
# 连接Redis
redis-cli -a 'R3dis$Secure#2024Pass!'

# 查看所有键
KEYS *

# 查看价格数据
ZRANGE price:binance:BTC/USDT:1m 0 -1 WITHSCORES

# 清空数据库
FLUSHDB
```

---

## Lana方法核心原则

### 8条铁律

1. **永远不预测启动** - 只在暴涨后介入
2. **裸K是唯一神** - 价格行为>一切指标
3. **入场越早越好** - 第一时间捕捉信号
4. **出场必须机械化** - 亏200u立即止损
5. **持仓极短(1小时)** - 快进快出
6. **真实成本优先** - 关注实际盈亏
7. **选币要动态** - 根据市场调整
8. **虎口夺食心态** - 敢于在高点做空

### Hermes执行要点

```python
# Lana规则严格执行
class LanaRuleEngine:
    def __init__(self):
        self.max_loss = 200  # USDT
        self.max_holding_time = 3600  # 1小时
        
    def check_trade(self, signal):
        # 1. 分数检查
        if signal['score'] < 85:
            return False
            
        # 2. 组合检查
        if 'OI_SPIKE' not in signal['types']:
            return False  # OI是必须的
            
        # 3. 价格检查
        if signal['price_change'] < 3:
            return False  # 价格未启动
            
        return True
        
    def execute_trade(self, signal):
        entry_price = signal['price']
        stop_loss = entry_price + (200 / position_size)
        
        # 开仓
        order = place_order(
            symbol=signal['symbol'],
            side='SELL',  # 做空
            size=calculate_size(200),
            stop_loss=stop_loss
        )
        
        # 设置1小时强制平仓
        schedule_close(order_id, after=3600)
```

---

## 下一步行动

### For Hermes Agent

1. ✅ **学习完成** - 理解crypto-monitor-bot架构
2. 🔄 **数据对接** - 连接PostgreSQL/Redis读取告警
3. 🎯 **策略实现** - 根据融合信号执行交易
4. 📊 **反馈优化** - 分析交易结果优化monitor参数
5. 🤖 **自动化** - 实现完全自动化交易流程

### 推荐阅读顺序

```
1. 本文档 (HERMES_AGENT_LEARNING_GUIDE.md)
   ↓
2. SYSTEM_OVERVIEW.md (架构详解)
   ↓
3. LANA_UPGRADE.md (Lana方法)
   ↓
4. src/analyzers/signal_fusion.py (信号融合代码)
   ↓
5. OPTIMIZATION_CONFIG.md (当前优化配置)
```

---

## 联系方式

- **部署服务器:** 119.28.43.237
- **Telegram Bot:** @your_crypto_monitor_bot
- **日志位置:** /var/log/crypto-monitor-bot.log
- **代码目录:** /opt/crypto-monitor-bot

---

**文档版本:** V1.0  
**最后更新:** 2026-04-16  
**状态:** ✅ 生产环境运行中  
**监控币种:** 167个  
**优化状态:** 已完成参数优化  

---

🎯 **Hermes Agent, 准备好成为加密货币交易大神了吗？Let's Go! 🚀**
