#!/bin/bash
# 从腾讯云服务器下载 Hermes Bot 代码

SERVER_IP="119.28.43.237"
SERVER_USER="root"
SERVER_PORT="22"

echo "📦 开始从服务器下载代码..."

# 创建目录存放服务器代码
mkdir -p hermes_server_code

# 下载最优化的版本
echo "⬇️  下载 crypto-bot-lana-optimized.tar.gz..."
scp -P ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP}:/root/crypto-bot-lana-optimized.tar.gz ./

# 解压到 hermes_server_code 目录
echo "📂 解压代码到 hermes_server_code/ ..."
tar -xzf crypto-bot-lana-optimized.tar.gz -C hermes_server_code/

# 同时下载环境变量文件和脚本（可选）
echo "⬇️  下载配置文件和脚本..."
scp -P ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP}:/root/hermes.env ./ 2>/dev/null || echo "⚠️  hermes.env 不存在，跳过"
scp -P ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP}:/root/start-hermes.sh ./ 2>/dev/null || echo "⚠️  start-hermes.sh 不存在，跳过"
scp -P ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP}:/root/deploy.sh ./ 2>/dev/null || echo "⚠️  deploy.sh 不存在，跳过"

echo "✅ 下载完成！"
echo "📊 服务器代码位置: hermes_server_code/"
ls -lh hermes_server_code/

echo ""
echo "🔍 接下来 Claude 将分析和整合代码..."
