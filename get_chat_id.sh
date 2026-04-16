#!/bin/bash
#
# 获取 Telegram Chat ID 的辅助脚本
#

BOT_TOKEN="$1"

if [ -z "$BOT_TOKEN" ]; then
    echo "使用方法: bash get_chat_id.sh YOUR_BOT_TOKEN"
    exit 1
fi

echo "================================================"
echo "步骤："
echo "1. 在 Telegram 中找到你的机器人"
echo "2. 给机器人发送任意一条消息（例如: /start 或 hello）"
echo "3. 按回车键继续..."
echo "================================================"
read -p "按回车键继续..."

echo ""
echo "正在获取更新..."
echo ""

curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates" | python3 -m json.tool | grep -A 5 '"chat"'

echo ""
echo "================================================"
echo "在上面的输出中找到："
echo "  \"id\": 123456789   <-- 这就是你的 Chat ID"
echo "================================================"
