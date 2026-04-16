#!/bin/bash
echo "=== 检查Binance API连通性 ==="
echo "1. 测试REST API:"
curl -s -m 5 "https://api.binance.com/api/v3/ping" && echo "✅ REST API 正常" || echo "❌ REST API 失败"

echo -e "\n2. 测试WebSocket:"
timeout 3 curl -s "https://stream.binance.com:9443/ws/btcusdt@ticker" | head -c 100 && echo "... ✅ WebSocket 可访问" || echo "❌ WebSocket 无法连接"

echo -e "\n3. 当前网络状态:"
netstat -an | grep -E "(9443|443)" | grep ESTABLISHED | wc -l | xargs echo "活动连接数:"
