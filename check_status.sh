#!/bin/bash
# Quick status check for crypto monitor bot

echo "🤖 加密货币监控机器人状态检查"
echo "================================"
echo ""

# Check if bot is running
if pgrep -f "python3 main.py" > /dev/null; then
    echo "✅ 机器人正在运行 (PID: $(pgrep -f 'python3 main.py'))"
else
    echo "❌ 机器人未运行"
    exit 1
fi

echo ""
echo "📊 数据库统计："
echo "----------------"

# Check PostgreSQL
psql -h localhost -U cryptobot -d crypto_monitor -c "
SELECT
    'Price Data' as table_name,
    COUNT(*) as total_rows,
    COUNT(DISTINCT symbol_id) as unique_symbols,
    MAX(timestamp) as latest_data
FROM price_data;
" 2>&1 | head -10

echo ""

# Check Redis
echo "📊 Redis 统计："
redis-cli -h localhost -p 6379 INFO keyspace | grep "keys=" || echo "  无数据"

echo ""
echo "📝 最近日志 (最后10行)："
echo "------------------------"
tail -10 logs/crypto_monitor_$(date +%Y-%m-%d).log 2>/dev/null || echo "  日志文件不存在"

echo ""
echo "================================"
echo "检查完成！"
