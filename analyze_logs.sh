#!/bin/bash

echo "========================================="
echo "📊 Phase 2 日志分析"
echo "========================================="

LOG_FILE="/root/crypto-monitor-phase1/bot_phase2.log"

if [ ! -f "$LOG_FILE" ]; then
    echo "❌ 日志文件不存在: $LOG_FILE"
    exit 1
fi

echo ""
echo "1️⃣  系统启动时间："
grep "Starting Phase 2" "$LOG_FILE" | tail -1

echo ""
echo "2️⃣  是否有信号生成："
SIGNAL_COUNT=$(grep -c "NEW SIGNAL" "$LOG_FILE")
echo "   总信号数: $SIGNAL_COUNT"

if [ "$SIGNAL_COUNT" -gt 0 ]; then
    echo ""
    echo "   最近的信号："
    grep "NEW SIGNAL" "$LOG_FILE" | tail -5
fi

echo ""
echo "3️⃣  策略统计（最新）："
grep "Phase 2 Stats" "$LOG_FILE" | tail -1

echo ""
echo "4️⃣  策略状态（最新）："
grep "策略状态" "$LOG_FILE" | tail -1

echo ""
echo "5️⃣  历史数据状态（最新）："
grep "历史数据状态" "$LOG_FILE" | tail -1

echo ""
echo "6️⃣  错误统计："
ERROR_COUNT=$(grep -c "ERROR" "$LOG_FILE")
echo "   错误总数: $ERROR_COUNT"

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo ""
    echo "   最近的错误："
    grep "ERROR" "$LOG_FILE" | tail -10
fi

echo ""
echo "7️⃣  限流统计："
RATE_LIMIT_COUNT=$(grep -c "Rate limited" "$LOG_FILE")
echo "   限流警告数: $RATE_LIMIT_COUNT"

echo ""
echo "8️⃣  数据采集统计（最新）："
grep "Phase 1 Stats" "$LOG_FILE" | tail -1

echo ""
echo "9️⃣  V4A 调试信息："
grep "V4A" "$LOG_FILE" | tail -20

echo ""
echo "🔟 Telegram 发送状态："
TELEGRAM_SUCCESS=$(grep -c "Signal sent to Telegram" "$LOG_FILE")
TELEGRAM_FAIL=$(grep -c "Failed to send Telegram" "$LOG_FILE")
echo "   成功: $TELEGRAM_SUCCESS"
echo "   失败: $TELEGRAM_FAIL"

echo ""
echo "========================================="
echo "✅ 分析完成"
echo "========================================="
