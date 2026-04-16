# 🐋 庄家行为检测系统设计

## 目标
在现有 MVP 基础上，增加庄家吸筹和出货信号检测。

---

## 方案 A：快速优化（仅用现有数据）

### 1. 量价背离检测
**吸筹信号**：价格横盘/下跌 + 交易量持续放大
```python
# 检测逻辑
if price_change < 5% and volume_increase > 200%:
    alert("疑似吸筹：放量不涨")
```

**出货信号**：价格上涨 + 交易量暴增
```python
if price_change > 10% and volume_spike > 500%:
    alert("疑似出货：放量拉升")
```

### 2. 交易量异常检测
- 对比过去 1 小时平均交易量
- 当前交易量 > 平均值 5 倍 → 警告
- 当前交易量 > 平均值 10 倍 → 严重警告

### 3. 波动率 + 交易量组合
| 价格变化 | 交易量   | 信号        |
|---------|---------|------------|
| +10%    | 5x      | 🚀 拉升出货  |
| -5%     | 3x      | 📉 洗盘吸筹  |
| ±2%     | 10x     | 🎭 对敲做市  |

**优点**：
- ✅ 无需额外 API 调用
- ✅ 1 小时可以实现
- ✅ 可以检测 70% 的明显庄家行为

**缺点**：
- ❌ 无法检测隐蔽的挂单操控
- ❌ 无法识别大单

---

## 方案 B：完整实现（需要订单簿数据）

### 1. 数据源扩展
需要接入 Binance 的额外 WebSocket 流：

#### **A. 订单簿深度流**
```bash
wss://stream.binance.com:9443/ws/btcusdt@depth20@100ms
```
获取：
- 前 20 档买单/卖单
- 挂单总量
- 买卖压力比

#### **B. 逐笔成交流**
```bash
wss://stream.binance.com:9443/ws/btcusdt@trade
```
获取：
- 每笔成交金额
- 主动买入/卖出标记
- 大单检测（单笔 > $100k）

### 2. 检测指标

#### 📈 **吸筹指标**
```python
class AccumulationDetector:
    def detect(self):
        # 1. 买单挂单量 > 卖单挂单量 1.5 倍
        bid_ask_ratio = total_bid_volume / total_ask_volume
        
        # 2. 价格横盘（±3% 波动）
        price_volatility = std(prices_last_hour)
        
        # 3. 交易量放大（> 2 倍平均值）
        volume_increase = current_volume / avg_volume
        
        if bid_ask_ratio > 1.5 and price_volatility < 3% and volume_increase > 2:
            return "吸筹信号"
```

#### 📉 **出货指标**
```python
class DistributionDetector:
    def detect(self):
        # 1. 卖单挂单量 > 买单挂单量
        sell_pressure = total_ask_volume / total_bid_volume
        
        # 2. 价格快速拉升
        price_spike = (current_price - price_1h_ago) / price_1h_ago
        
        # 3. 大额卖单频繁出现
        large_sell_orders = count_large_sells(last_10_min)
        
        if sell_pressure > 1.5 and price_spike > 8% and large_sell_orders > 5:
            return "出货信号"
```

#### 🐋 **大单追踪**
```python
LARGE_ORDER_THRESHOLD = 100_000  # $100k USD

class WhaleTracker:
    def track_trade(self, trade):
        order_size = trade['quantity'] * trade['price']
        
        if order_size > LARGE_ORDER_THRESHOLD:
            if trade['is_buyer_maker']:  # 主动买入
                alert(f"🐋 大额买单: ${order_size:,.0f}")
            else:  # 主动卖出
                alert(f"🐳 大额卖单: ${order_size:,.0f}")
```

### 3. 实现步骤

1. **新增数据收集器**
   - `DepthCollector` - 订单簿深度
   - `TradeCollector` - 逐笔成交

2. **新增分析器**
   - `AccumulationDetector` - 吸筹检测
   - `DistributionDetector` - 出货检测
   - `WhaleTracker` - 大单追踪

3. **优化存储**
   - Redis 存储最近 1 小时订单簿快照
   - PostgreSQL 存储大单记录

**优点**：
- ✅ 完整的庄家行为识别
- ✅ 可以检测隐蔽操作
- ✅ 提供大单实时追踪

**缺点**：
- ❌ 开发时间 2-3 天
- ❌ 数据量增加（需要更多存储）
- ❌ API 调用频率更高

---

## 推荐路径

### 🚀 **第一阶段（今晚完成）**
使用 **方案 A**，立即增加：
1. 交易量异常检测
2. 量价背离分析
3. 简单的波动 + 量组合信号

### 🎯 **第二阶段（本周末）**
实现 **方案 B** 的部分功能：
1. 接入订单簿深度数据
2. 买卖压力比分析
3. 挂单量对比

### 🏆 **第三阶段（下周）**
完整实现：
1. 大单追踪
2. 对敲检测
3. 历史模式匹配

---

## 立即可用的快速检测规则

基于现有数据，我可以立即实现：

| 场景 | 条件 | 信号 |
|-----|------|-----|
| 放量不涨 | 价格变化 < 3% 且 交易量 > 5x | 🟢 疑似吸筹 |
| 放量拉升 | 价格上涨 > 10% 且 交易量 > 5x | 🔴 疑似出货 |
| 缩量上涨 | 价格上涨 > 8% 且 交易量 < 2x | ⚠️ 假突破 |
| 放量下跌 | 价格下跌 > 10% 且 交易量 > 5x | 💀 恐慌出逃 |

---

## 下一步行动

你想要：
1. **快速见效** → 现在开始实现方案 A（30 分钟）
2. **完整方案** → 本周实现方案 B（需要 2-3 天）
3. **先测试** → 让机器人继续跑，手动观察现有告警是否有用

告诉我你的选择！
