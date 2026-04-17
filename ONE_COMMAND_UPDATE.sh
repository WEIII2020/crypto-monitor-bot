#!/bin/bash
# 一键升级到 200 币种 - v2.0-unified

echo "🚀 开始升级到 v2.0-unified-200..."

cd /root/crypto-monitor-bot || exit 1

# 1. 备份
echo "📦 备份旧配置..."
cp .env /tmp/.env.backup 2>/dev/null || true
cp config.yaml config.yaml.backup
cp main.py main.py.backup

# 2. 更新 config.yaml
echo "⚙️ 更新 config.yaml..."
cat > config.yaml << 'CONFIGEND'
# Crypto Monitor Bot Configuration
symbols:
  max_count: 200
  min_volume_usd: 1000000
  max_volume_usd: 500000000
  min_price: 0.01
  max_price: 10.0
whale_detection:
  volume_spike_threshold: 5.0
  volume_low_threshold: 2.0
  sideways_threshold: 3.0
  significant_rise: 10.0
  moderate_rise: 8.0
  significant_drop: 10.0
volatility:
  warning_threshold: 10.0
  critical_threshold: 20.0
alerts:
  price_spike_cooldown: 600
  whale_activity_cooldown: 600
  enable_priority: false
performance:
  stats_interval: 300
  max_concurrent_writes: 50
database:
  pool_size: 20
  max_overflow: 10
  pool_recycle: 3600
monitoring:
  check_interval: 30
  data_retention_days: 180
pump_dump_strategy:
  enabled: false
  pump_threshold: 20.0
  stop_loss_pct: 3.0
  take_profit_1: 5.0
  take_profit_2: 10.0
  max_holding_hours: 2
  min_manipulation_score: 60
CONFIGEND

# 3. 更新 main.py
echo "⚙️ 更新 main.py..."
sed -i 's/max_symbols=50/max_symbols=200/g' main.py

# 4. 更新 symbol_selector.py
echo "⚙️ 更新 symbol_selector.py..."
sed -i 's/min_volume_usd = 5_000_000/min_volume_usd = 1_000_000/g' src/utils/symbol_selector.py
sed -i 's/max_volume_usd = 50_000_000/max_volume_usd = 500_000_000/g' src/utils/symbol_selector.py
sed -i 's/max_symbols: int = 50/max_symbols: int = 200/g' src/utils/symbol_selector.py

# 5. 停止旧服务
echo "🛑 停止旧服务..."
pkill -f "python.*main.py" 2>/dev/null || true
sleep 2

# 6. 启动新服务
echo "🚀 启动新服务..."
./start.sh

sleep 5

echo ""
echo "==============================================="
echo "✅ 升级完成！"
echo "==============================================="
echo ""
echo "📊 版本: v2.0-unified-200"
echo "📈 监控币种: 200 个"
echo ""
echo "📝 查看日志验证："
echo "   tail -f logs/crypto_monitor_*.log"
echo ""
echo "应该看到："
echo "   ✅ Selected 200 symbols"
echo "   ✅ Bot is running!"
echo ""
echo "==============================================="
