#!/bin/bash

echo "=== Bot运行状态诊断 ==="
echo ""

echo "1. 进程状态:"
PID=$(cat bot.pid 2>/dev/null)
if [ -n "$PID" ] && ps -p $PID > /dev/null 2>&1; then
    ps -p $PID -o pid,etime,%cpu,%mem,command | tail -1
    echo "   ✅ 进程运行中 (PID: $PID)"
else
    echo "   ❌ 进程未运行"
fi

echo ""
echo "2. 数据库连接:"
redis-cli ping > /dev/null 2>&1 && echo "   ✅ Redis: 正常" || echo "   ❌ Redis: 失败"
pg_isready -h localhost > /dev/null 2>&1 && echo "   ✅ PostgreSQL: 正常" || echo "   ❌ PostgreSQL: 失败"

echo ""
echo "3. Redis数据检查:"
KEY_COUNT=$(redis-cli keys "binance:*" | wc -l)
echo "   Binance键数量: $KEY_COUNT"
if [ "$KEY_COUNT" -gt "0" ]; then
    echo "   示例数据:"
    redis-cli keys "binance:*" | head -3 | while read key; do
        echo "     $key"
    done
else
    echo "   ⚠️  没有数据"
fi

echo ""
echo "4. 最近日志 (最后10行):"
tail -10 logs/crypto_monitor_2026-04-15.log | sed 's/^/   /'

echo ""
echo "5. 错误统计 (最近1分钟):"
ERROR_COUNT=$(grep -c "ERROR" logs/crypto_monitor_2026-04-15.log 2>/dev/null || echo 0)
WARN_COUNT=$(grep -c "WARNING" logs/crypto_monitor_2026-04-15.log 2>/dev/null || echo 0)
echo "   ERROR: $ERROR_COUNT"
echo "   WARNING: $WARN_COUNT"

echo ""
echo "=== 诊断完成 ==="
