# 🚀 Phase 1 部署指南 - 毫秒级实时监控

## 📋 系统升级概览

### 核心改进

| 指标 | 旧系统 | 新系统（Phase 1） | 提升 |
|------|--------|------------------|------|
| **数据延迟** | ~1秒 | **10-50ms** | **20-100倍** |
| **数据粒度** | 24h汇总 | **逐笔成交** | **∞** |
| **买卖压力** | ❌ 不支持 | ✅ 实时 | **新增** |
| **大单检测** | ⚠️ 延迟 | ✅ 毫秒级 | **新增** |
| **内存效率** | Redis查询 | **内存滑动窗口** | **10倍+** |

---

## 🏗️ 架构变化

### 新增组件

```
crypto-monitor-bot/
├── src/
│   ├── collectors/
│   │   ├── binance_collector.py          # 旧：24hrTicker
│   │   └── binance_realtime_collector.py # 新：aggTrade (毫秒级) ⭐
│   └── utils/
│       └── sliding_window.py             # 新：内存滑动窗口 ⭐
├── main.py                                # 旧版主程序
├── main_realtime.py                       # 新版主程序 ⭐
└── tests/
    └── test_realtime_system.py           # 性能测试 ⭐
```

### 数据流对比

**旧系统**：
```
Binance WebSocket (24hrTicker, 1秒更新)
    ↓
Redis 存储
    ↓
分析器每30秒查询 Redis
    ↓
告警
```

**新系统**：
```
Binance WebSocket (aggTrade, 逐笔推送)
    ↓ (10-50ms 延迟)
内存滑动窗口 (O(1) 写入)
    ↓ (< 1ms 查询)
实时分析器 (1秒检查)
    ↓
告警
```

---

## 🧪 本地测试

### Step 1: 安装依赖

```bash
cd /Users/szld2403203/Library/Mobile\ Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot

# 激活虚拟环境
source venv/bin/activate

# 安装新依赖（numpy）
pip install numpy
```

### Step 2: 运行测试套件

```bash
# 测试1: 延迟测试（验证 10-50ms 延迟）
python tests/test_realtime_system.py

# 预期输出:
# ✅ Average latency < 100ms
# ✅ Query < 1ms
```

**预期结果**：
```
╔════════════════════════════════════
║ 📊 Latency Test Results
╠════════════════════════════════════
║ Total Trades: 150-300
║ Avg Latency: 20-50 ms  ✅
║ Min Latency: 10-20 ms
║ Max Latency: 80-150 ms
║ Trades/sec: 15-30
╚════════════════════════════════════
```

### Step 3: 小规模实时测试（5个币种）

```bash
# 修改 main_realtime.py 第47行
# test_mode = True  # 开启测试模式

python main_realtime.py

# 观察输出（30秒后 Ctrl+C 停止）
```

**预期输出**：
```
🚀 Starting Realtime Crypto Monitor Bot...
✅ Database connections established
🧪 Test mode: monitoring 5 symbols
✅ Subscribed to 5 realtime streams
✅ Realtime Bot is running!

⚡ BTC/USDT 1m price spike: +1.23% (Buy: 65.2%, Sell: 34.8%)
🐋 ETH/USDT Large order: BUY $125,000 @ $2,450.00
📊 Performance: 1,234 trades, 41.1 trades/s, 25.3ms latency, 5 symbols
```

---

## 🚀 服务器部署

### Step 1: 上传新文件

在**本地终端**执行：

```bash
# 打包新文件
cd /Users/szld2403203/Library/Mobile\ Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot

tar -czf /tmp/phase1-realtime.tar.gz \
  src/collectors/binance_realtime_collector.py \
  src/utils/sliding_window.py \
  main_realtime.py \
  tests/test_realtime_system.py

# 上传到服务器（使用 Cyberduck 或 SCP）
# 目标路径: /root/phase1-realtime.tar.gz
```

### Step 2: 服务器安装

在**服务器终端**执行：

```bash
cd /root/crypto-monitor-bot

# 解压新文件
tar -xzf /root/phase1-realtime.tar.gz

# 安装新依赖
source venv/bin/activate
pip install numpy

# 测试
python tests/test_realtime_system.py
```

### Step 3: 启动实时监控

```bash
cd /root/crypto-monitor-bot
source venv/bin/activate

# 方式 A: 测试模式（5个币种，验证功能）
# 修改 main_realtime.py: test_mode = True
nohup python main_realtime.py > bot_realtime_test.log 2>&1 &

# 等待10秒后查看日志
sleep 10
tail -50 bot_realtime_test.log

# 如果看到 "trades/s" 和 "ms latency" 输出，说明成功！

# 方式 B: 生产模式（200个币种）
# 修改 main_realtime.py: test_mode = False
pkill -f "python.*main_realtime.py"  # 先停止测试
nohup python main_realtime.py > bot_realtime.log 2>&1 &
echo $! > bot_realtime.pid

# 查看日志
tail -f bot_realtime.log
```

---

## 📊 性能验证

### 关键指标

运行后，应该看到类似输出：

```bash
tail -f bot_realtime.log | grep "Performance"

# 每30秒输出一次：
📊 Performance: 5,432 trades, 180.5 trades/s, 23.1ms latency, 200 symbols
📊 Performance: 10,821 trades, 180.3 trades/s, 24.5ms latency, 200 symbols
```

**健康指标**：
- ✅ `trades/s` > 100（200个币种）
- ✅ `latency` < 100ms
- ✅ `active_symbols` = 200

**异常指标**：
- ❌ `trades/s` < 50 → 检查网络连接
- ❌ `latency` > 200ms → 检查服务器性能
- ❌ `active_symbols` < 200 → 检查订阅是否成功

---

## 🔍 实时监控示例

### 1. 价格剧烈波动

```
⚡ SOL/USDT 1m price spike: +2.35% (Buy: 72.1%, Sell: 27.9%)
```

**解读**：
- 1分钟涨幅 +2.35%（快速拉升）
- 买方主导（72.1% 主动买入）
- **信号**：可能继续上涨，观察

### 2. 买卖压力失衡

```
🔴 DOGE/USDT Strong selling pressure: 28.3%
```

**解读**：
- 买入比例仅 28.3%（卖方主导）
- **信号**：做空机会，等待确认

### 3. 成交量异常

```
📊 SHIB/USDT Volume spike: 4.2x
```

**解读**：
- 成交量突增 4.2 倍
- **信号**：关注后续价格变化

### 4. 大单检测

```
🐋 BTC/USDT Large order: BUY $250,000 @ $42,150.00
🐋 BTC/USDT Large order: SELL $180,000 @ $42,155.00
```

**解读**：
- 巨额买卖单频繁出现
- **信号**：机构在博弈，关注方向

---

## 🆚 新旧系统对比

### 场景1: 捕捉暴涨启动点

**旧系统**：
```
时间 14:30:00 - 价格 $100（24h数据汇总）
时间 14:30:30 - 价格 $105（延迟发现，+5%）❌ 错过入场
```

**新系统**：
```
时间 14:30:00.123 - 价格 $100.00
时间 14:30:01.456 - 价格 $100.50 (+0.5%)
时间 14:30:02.789 - 价格 $101.20 (+1.2%)
⚡ 检测到异常，买入比例 75%
✅ 14:30:03 入场 @ $101.50（及时捕捉）
```

### 场景2: 检测Dump信号

**旧系统**：
```
1分钟前：涨幅 +20%
现在：跌到 +15%（已回撤 -5%）
❌ 太晚，错过做空最佳点
```

**新系统**：
```
14:45:30.123 - 价格触顶 $120（+20%）
14:45:31.456 - 大卖单 $80K（卖压出现）
14:45:32.789 - 买卖比 38%（确认Dump）
⚡ 立即发出做空信号 @ $119.50
✅ 抓住回撤前3秒黄金时间
```

---

## ⚙️ 配置调优

### 调整监控频率

```python
# main_realtime.py 第115行
check_interval_ms = 1000  # 默认1秒检查一次

# 更激进（高频交易）：
check_interval_ms = 500   # 0.5秒

# 更保守（减少CPU）：
check_interval_ms = 2000  # 2秒
```

### 调整告警阈值

```python
# main_realtime.py 第135行
if abs(price_change) > 2.0:  # 默认2%

# 更敏感：
if abs(price_change) > 1.0:  # 1%

# 更严格：
if abs(price_change) > 3.0:  # 3%
```

### 调整大单阈值

```python
# main_realtime.py 第152行
large_orders = await self.collector.get_large_orders(symbol, min_usdt=50000)

# 只看巨鲸（更高阈值）：
large_orders = await self.collector.get_large_orders(symbol, min_usdt=100000)

# 看所有大单（更低阈值）：
large_orders = await self.collector.get_large_orders(symbol, min_usdt=20000)
```

---

## 🐛 故障排查

### 问题1: 收不到数据

```bash
# 检查日志
tail -100 bot_realtime.log | grep -i "error"

# 常见原因：
# 1. WebSocket 连接失败 → 检查网络
# 2. 订阅失败 → 检查币种格式（BTC/USDT）
# 3. 防火墙阻止 → 检查 443 端口
```

### 问题2: 延迟过高

```bash
# 查看性能
tail -f bot_realtime.log | grep "latency"

# 如果 latency > 200ms:
# 1. 检查服务器负载: top
# 2. 检查网络延迟: ping stream.binance.com
# 3. 减少监控币种数量（测试）
```

### 问题3: 内存占用高

```bash
# 查看内存使用
ps aux | grep python | grep main_realtime

# 优化方法：
# 1. 减少 max_trades（src/utils/sliding_window.py 第87行）
# 2. 减少窗口时间（默认60秒）
# 3. 定期清理过期数据
```

---

## 📈 下一步（Phase 2 预告）

Phase 1 完成后，你将拥有：
- ✅ 毫秒级数据采集
- ✅ 实时买卖压力监控
- ✅ 大单即时检测

**Phase 2 将增加**：
- 🧠 做空信号生成器（你要的格式）
- 📊 6小时涨幅计算
- 🎯 Pump后Dump捕捉
- 📱 优化的 Telegram 推送

准备好进入 Phase 2 了吗？告诉我！🚀
