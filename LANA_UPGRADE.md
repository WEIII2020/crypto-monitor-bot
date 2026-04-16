# 🚀 Lana方法优化 - 云端部署指南

## 📦 优化内容

### 新增3个核心模块

1. **OI监控器** (`oi_monitor.py`)
   - 检测48h内OI变动>50%，价格<5%
   - lana核心信号：资金提前埋伏

2. **广场热度监控** (`square_monitor.py`)
   - 追踪币安广场讨论热度
   - lana核心信号：散户进场早期信号

3. **信号融合器** (`signal_fusion.py`)
   - 多维度评分系统
   - 黄金组合加成逻辑
   - 行动建议：≥60分WATCH，≥80分BUY

### 评分权重（lana方法）

```
OI异常:      40分  ← 最重要
价格波动:    30分
巨鲸行为:    20分
广场热度:    10分
朋友方法:    30分
─────────────────
黄金组合加成: 最高+20分
```

---

## 🔄 部署步骤

### 步骤1：上传代码

**文件位置**:
```
/Users/szld2403203/Library/Mobile Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot/crypto-bot-lana-optimized.tar.gz
```

**上传方式**:
1. 打开腾讯云网页终端
2. 使用「上传文件」功能
3. 上传到 `/root/` 目录

### 步骤2：部署命令

在腾讯云网页终端执行：

```bash
# 1. 备份当前版本
cd /opt
cp -r crypto-monitor-bot crypto-monitor-bot.backup.lana_$(date +%Y%m%d_%H%M%S)

# 2. 解压新代码（覆盖）
cd /opt/crypto-monitor-bot
tar -xzf /root/crypto-bot-lana-optimized.tar.gz

# 3. 配置文件已存在，无需修改

# 4. 安装依赖（如有新增）
source venv/bin/activate
pip install -q -r requirements.txt

# 5. 测试运行（15秒）
echo "🧪 测试运行15秒..."
timeout 15 venv/bin/python3 main.py || true

echo ""
echo "✅ 期望看到："
echo "   ✓ Selected 44-46 symbols"
echo "   ✓ Bot is running!"
echo "   ✓ 无错误信息"
echo ""

read -p "测试成功了吗？按回车继续部署... " dummy

# 6. 重启服务
supervisorctl restart crypto-monitor-bot

# 7. 等待5秒
sleep 5

# 8. 查看状态和日志
echo "📊 服务状态:"
supervisorctl status crypto-monitor-bot

echo ""
echo "📝 最新日志:"
tail -n 50 /var/log/crypto-monitor-bot.log

echo ""
echo "✅ 部署完成！"
echo ""
echo "💡 实时日志: tail -f /var/log/crypto-monitor-bot.log"
```

---

## ✅ 验证清单

部署后确认：

- [ ] 服务状态：`RUNNING`
- [ ] 日志显示：`Selected 44-46 symbols`
- [ ] 日志显示：5个任务启动（collector, volatility, whale, pump_dump, oi, fusion）
- [ ] 无错误信息
- [ ] Telegram收到消息

---

## 📊 新系统架构

```
数据采集层
├─ BinanceCollector (价格 + 成交量)
└─ OIMonitor (持仓量)  ← 新增

分析器层
├─ VolatilityDetector (30s)
├─ WhaleDetectorV2 (60s)
├─ PumpDumpDetector (智能频率)
└─ OIMonitor (120s)  ← 新增

信号融合层  ← 新增
└─ SignalFusion (60s)
    ├─ 多维度评分
    ├─ 黄金组合加成
    └─ 行动建议

输出层
└─ TelegramNotifier
```

---

## 🎯 预期效果

### 告警类型

**单一信号告警**（和之前一样）:
- 价格波动告警
- 巨鲸行为告警
- OI异常告警（新增）

**融合信号告警**（新增）:
```
🟢 综合信号 - BUY

🪙 BTC/USDT
💰 现价: $60,000

📊 综合评分: 85/100

🔍 触发信号 (3个):
  • OI_SPIKE: 40分
  • PRICE_SPIKE: 30分
  • SQUARE_TRENDING: 10分

⚡ 组合加成: +15分

🎯 建议行动: BUY

✅ 买入信号确认:
  • 多个信号同时触发
  • 综合评分达到85分
  • 建议：轻仓试探
  • 止损：严格执行（lana规则：亏200u出）
```

---

## 🔧 故障排查

### 问题1：OI监控无数据

```bash
# 测试OI API
cd /opt/crypto-monitor-bot
source venv/bin/activate
python3 -c "
import asyncio
from src.analyzers.oi_monitor import OIMonitor

async def test():
    monitor = OIMonitor()
    oi = await monitor._get_current_oi('BTC/USDT')
    print(f'BTC OI: {oi}')

asyncio.run(test())
"
```

### 问题2：信号融合不工作

查看日志：
```bash
grep "信号融合" /var/log/crypto-monitor-bot.log
```

应该看到每60秒的融合记录。

---

## 📈 下一步优化

1. **接入真实的币安广场API**
   - 目前使用模拟数据
   - 需要实现实际的爬虫或API

2. **集成hermes-agent-bot（自动交易）**
   - 接收crypto-monitor-bot的信号
   - 执行自动下单
   - lana规则执行

3. **内容自动发布**
   - 开仓后发币安广场帖子
   - 维持热度
   - 增加曝光

---

## 💡 重要提示

- 当前系统是**监控+告警**，不会自动交易
- 需要手动根据告警执行交易
- 自动交易功能将在hermes-agent-bot中实现
- 严格遵守lana规则：**亏200u立即止损**

---

**部署完成时间**: 2026-04-15  
**版本**: V3 - Lana Method Optimized
