# 🎯 Phase 2: 交易信号生成系统

> **目标**: 在 Phase 1 毫秒级监控基础上，增加智能交易信号生成（做多/做空双向 + 妖币策略）

---

## 🆕 Phase 2 新增功能

### 1️⃣ **妖币识别与评分**

基于 [@thecryptoskanda](https://x.com/thecryptoskanda/status/2042230477449531538) 的量化研究：

#### 核心指标
- **Binance OI 占比**：越低 → 操纵程度越高
- **vol/OI 比率**：≥ 20x → 刷量严重，过滤
- **现货控盘率**：> 96% → 高度操纵

#### 评分系统
```python
操纵评分 (0-100):
  70-100 = EXTREME（极端操纵）
  50-69  = HIGH（高度操纵）
  30-49  = MEDIUM（中度操纵）
  0-29   = LOW（低操纵）
```

---

### 2️⃣ **四大交易策略**

#### V4A: 支撑崩塌做空（早进策略）

**核心理念**：在妖币上，入场早的重要性 >> 确认得很稳

**触发条件（ALL）**：
1. 操纵评分 ≥ 50
2. 1H K线收阴，跌破支撑 2%+
3. 卖压主导（买入比 < 45%）
4. **只看裸 K**，不看量、不看振幅

**交易参数**：
- 止损：+3%（反向反弹立即出场）
- 持仓时间：< 1 小时（极短）
- 仓位：5-10%

**示例信号**：
```
╔════════════════════════════
║ 🔴 做空信号 - ETHUSDT
║ 策略: V4A 支撑崩塌
╠════════════════════════════
║ 📊 市场数据：
║   • 操纵评分: 85/100 ⚠️
║   • 入场价格: $2,380
║   • 止损价格: $2,451 (+3%)
║   • 目标1: $2,261 (-5%)
║   • 目标2: $2,142 (-10%)
║
║ 💡 交易建议：
║   • 方向: 做空 📉
║   • 仓位: 5-10%
║   • 持仓: <1小时
║   • 置信度: 87% ✅
║
║ ⚠️ 风险提示：
║   虎口夺食，快进快出！
╚════════════════════════════
```

---

#### V7: 价格OI背离做空（聪明钱撤退）

**核心理念**：价格被托涨，但聪明钱在撤退

**触发条件**：
1. 4小时内价格上涨 5%+
2. 同时 OI 连续下降 10%+
3. 价格 vs OI 背离

**交易参数**：
- 止损：+5%
- 目标1：-5%
- 目标2：-10%
- **需紧跟 trailing 止盈**

**优势**：
- 与 V4A 重合度低（互补）
- 捕捉聪明钱退场时机

---

#### V8: 插针+OI骤降做空（空头真空）

**核心理念**：比纯 K线 快 2-4 小时

**触发条件（ALL）**：
1. 操纵币种（评分 ≥ 50）
2. 急速插针（上影线 > 5%）
3. 30分钟内 OI 骤降 15%+
4. 插针后价格回落 3%+

**交易参数**：
- 止损：插针高点上方 2%
- 目标1：-7%
- 目标2：-15%

**优势**：
- **最强 V4A 补充**
- 触发速度极快
- 几乎不重合

---

#### LONG: 反弹做多（抄底策略）

**核心理念**：大跌后反弹，买方主导

**触发条件（ALL）**：
1. **非**极端操纵币种（评分 < 70）
2. 1H内大跌 5%+ 后反弹 2%+
3. 买方主导（买入比 > 70%）
4. OI 上升 5%+（资金流入）

**交易参数**：
- 止损：低点下方 2%
- 目标1：+5%
- 目标2：+8%
- 持仓：< 2 小时

**风险**：
- 风险低于做空
- 快进快出

---

### 3️⃣ **信号置信度系统**

每个信号都有 **0-100 分**的置信度评分：

#### 计算因素

| 因素 | 权重 | 说明 |
|------|------|------|
| **策略类型** | 15-30分 | V8(30) > V4A(25) > V7(20) > LONG(15) |
| **操纵评分** | 10-15分 | EXTREME(+15), HIGH(+10) |
| **信号强度** | 5-15分 | 跌破幅度、背离强度、插针幅度 |

#### 置信度等级

```
90-100 = 极强信号 ✅✅✅
70-89  = 强信号 ✅✅
50-69  = 中等信号 ✅
< 50   = 弱信号（不推送）
```

---

### 4️⃣ **智能冷却期**

防止重复告警：

| 策略 | 冷却期 |
|------|--------|
| V4A | 4 小时 |
| V7 | 4 小时 |
| V8 | 2 小时 |
| LONG | 2 小时 |

同一币种同一策略在冷却期内不会重复推送。

---

## 📊 系统架构

```
┌─────────────────────────────────────────────────────┐
│              Phase 1: 毫秒级数据采集                 │
│   • Binance aggTrade WebSocket                      │
│   • 滑动窗口（买卖压力、大单检测）                    │
└────────────────┬────────────────────────────────────┘
                 │ 实时数据
                 ↓
┌─────────────────────────────────────────────────────┐
│            Phase 2: 交易信号生成                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1️⃣ 妖币检测器 (ManipulationDetectorV2)             │
│     ├─ Binance OI 占比                              │
│     ├─ vol/OI 过滤                                  │
│     └─ 操纵评分 (0-100)                             │
│                                                     │
│  2️⃣ 信号生成器 (TradingSignalGenerator)            │
│     ├─ V4A: 支撑崩塌                                │
│     ├─ V7: 价格OI背离                               │
│     ├─ V8: 插针+OI骤降                              │
│     └─ LONG: 反弹做多                               │
│                                                     │
│  3️⃣ 信号优先级排序                                  │
│     └─ 按置信度降序                                  │
│                                                     │
│  4️⃣ 冷却期检查                                      │
│     └─ 防重复告警                                    │
│                                                     │
└────────────────┬────────────────────────────────────┘
                 │ 格式化信号
                 ↓
┌─────────────────────────────────────────────────────┐
│              Telegram 推送 + 日志                    │
└─────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 前提条件

Phase 2 依赖 Phase 1，请先确保 Phase 1 运行正常：

```bash
cd /root/crypto-monitor-phase1
source venv/bin/activate

# 测试 Phase 1
python tests/test_realtime_system.py
```

### 启动 Phase 2

#### 方式 A: 测试模式（5币种）

```bash
cd /root/crypto-monitor-phase1
source venv/bin/activate

# 修改 main_phase2.py 第50行
# self.test_mode = True

# 启动
python main_phase2.py
```

#### 方式 B: 生产模式（200币种）

```bash
cd /root/crypto-monitor-phase1
source venv/bin/activate

# self.test_mode = False（默认）

# 后台运行
nohup python main_phase2.py > bot_phase2.log 2>&1 &
echo $! > bot_phase2.pid

# 查看日志
tail -f bot_phase2.log
```

---

## 📈 预期输出

### 启动日志

```
🚀 Starting Phase 2 Trading Signal System...
✅ Database connections established
✅ Selected 200 symbols
✅ Subscribed to 200 symbols
🔍 Starting signal generation...
📈 Starting stats monitor...
✅ Phase 2 system is running!
```

### 信号输出

```
==================================================
🎯 NEW SIGNAL: SHIB/USDT - V4A_SHORT
==================================================

╔════════════════════════════
║ 🔴 做空信号 - SHIB/USDT
║ 策略: V4A 支撑崩塌
╠════════════════════════════
║ 📊 市场数据：
║   • 操纵评分: 78/100 ⚠️
║   • 入场价格: $0.00000965
║   • 止损价格: $0.00000995 (+3.1%)
║   • 目标1: $0.00000917 (-5.0%)
║   • 目标2: $0.00000869 (-10.0%)
║
║ 💡 交易建议：
║   • 方向: 做空 📉
║   • 仓位: 5-10%
║   • 持仓: <1小时
║   • 置信度: 82% ✅
║
║ ⚠️ 风险提示：
║   虎口夺食，快进快出！
╚════════════════════════════

✅ Signal sent to Telegram
==================================================
```

### 性能统计（每60秒）

```
📊 Phase 2 Stats: 12 signals (V4A:5, V7:3, V8:2, LONG:2) | Sent: 12
📊 Phase 1 Stats: 180.5 trades/s, 25.3ms latency
```

---

## ⚙️ 配置调优

### 调整操纵评分阈值

```python
# src/analyzers/manipulation_detector_v2.py

# 更严格（只监控极端操纵币）
self.binance_oi_threshold = 0.3  # Binance OI < 30%

# 更宽松（监控更多币种）
self.binance_oi_threshold = 0.5  # Binance OI < 50%
```

### 调整 V4A 灵敏度

```python
# src/analyzers/manipulation_detector_v2.py

# 更激进（早进）
self.v4a_support_break = 0.015  # 跌破 1.5%

# 更保守（确认后再进）
self.v4a_support_break = 0.03   # 跌破 3%
```

### 调整信号冷却期

```python
# src/analyzers/trading_signal_generator.py

# 更频繁（更多信号）
self.signal_cooldown = {
    'V4A_SHORT': 7200,   # 2 小时
    'V7_SHORT': 7200,
    'V8_SHORT': 3600,    # 1 小时
    'LONG': 3600
}

# 更保守（减少噪音）
self.signal_cooldown = {
    'V4A_SHORT': 21600,  # 6 小时
    'V7_SHORT': 21600,
    'V8_SHORT': 14400,   # 4 小时
    'LONG': 14400
}
```

---

## 🐛 故障排查

### Q1: 收不到信号

**可能原因**：
1. Phase 1 数据采集问题 → 检查 Phase 1 日志
2. 阈值设置过严 → 降低操纵评分要求
3. 市场太清淡 → 正常现象

**排查**：
```bash
# 查看是否有操纵币种被识别
tail -f bot_phase2.log | grep "manipulation_score"

# 查看是否有信号被冷却期过滤
tail -f bot_phase2.log | grep "cooldown"
```

### Q2: 信号质量差

**优化方案**：
1. 提高置信度阈值（只发 >70% 的信号）
2. 增加操纵评分要求（只监控 EXTREME 币种）
3. 启用更严格的过滤（vol/OI < 15x）

### Q3: Telegram 推送失败

**排查**：
```bash
# 检查 .env 配置
grep TELEGRAM /root/crypto-monitor-phase1/.env

# 测试 Telegram连接
python -c "from src.notifiers.telegram_notifier import TelegramNotifier; import asyncio; asyncio.run(TelegramNotifier().send_message('Test'))"
```

---

## 📚 与 Hermes Agent 集成

Phase 2 的信号可以直接发送给 Hermes Agent 执行交易：

### 集成方式

```python
# 在 main_phase2.py 的 _handle_signal 中添加：

# 发送给 Hermes
hermes_message = {
    'type': 'TRADING_SIGNAL',
    'signal': {
        'symbol': signal.symbol,
        'direction': signal.direction,
        'entry': signal.entry_price,
        'stop_loss': signal.stop_loss,
        'take_profit': signal.take_profit_1,
        'confidence': signal.confidence,
        'strategy': signal.strategy
    }
}

# 通过 API 或消息队列发送
await hermes_client.send(hermes_message)
```

### Hermes 决策逻辑

Hermes 可以根据以下条件决定是否执行：
- 置信度 ≥ 80% → 自动执行
- 置信度 60-79% → 人工确认
- 置信度 < 60% → 仅记录，不执行

---

## 🎓 核心理念

Phase 2 基于 @thecryptoskanda 的研究，核心理念：

1. **妖币不是预测，而是识别**
   - 不要预测启动
   - 识别已经启动的妖币

2. **入场早 > 确认稳**
   - V4A：第一时间入场
   - 不等充分确认

3. **持仓短 > 盈利大**
   - 中位数持仓 1 小时
   - 快进快出

4. **止损严 > 盈亏比**
   - 反向 3% 立即出场
   - 不抱幻想

5. **机会多 > 单次赚**
   - 70 个监控组
   - 每天 2-3 个信号

---

## 🚀 下一步（Phase 3）

Phase 3 将实现：
- ✅ 自动交易执行
- ✅ 仓位管理
- ✅ 多账户支持
- ✅ 回测系统
- ✅ 风险控制

准备好了吗？🎉
