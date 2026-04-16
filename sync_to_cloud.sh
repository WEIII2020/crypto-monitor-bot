#!/bin/bash
#
# 同步优化后的代码到云端服务器
# 服务器: 119.28.43.237
#

set -e

SERVER_IP="119.28.43.237"
PROJECT_DIR="/Users/szld2403203/Library/Mobile Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot"

echo "================================================"
echo "同步优化后的代码到云端"
echo "服务器: $SERVER_IP"
echo "================================================"
echo ""

cd "$PROJECT_DIR"

echo "📦 打包优化后的代码..."
tar -czf crypto-bot-optimized.tar.gz \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='venv' \
  --exclude='.env' \
  --exclude='bot.pid' \
  --exclude='.DS_Store' \
  --exclude='*.log' \
  --exclude='test_*.py' \
  --exclude='code.tar.gz' \
  --exclude='crypto-bot.tar.gz' \
  main.py \
  src/ \
  requirements.txt \
  config.yaml

echo "✅ 打包完成: crypto-bot-optimized.tar.gz"
echo ""

echo "📤 上传到服务器..."
echo "⚠️  需要输入服务器密码"
echo ""

# 上传代码包
scp crypto-bot-optimized.tar.gz root@$SERVER_IP:/root/

echo ""
echo "================================================"
echo "✅ 上传完成！"
echo "================================================"
echo ""
echo "📋 下一步：在腾讯云网页终端执行以下命令"
echo ""
echo "-------- 复制下面的命令 --------"
echo ""
cat << 'DEPLOY_COMMANDS'
# 1. 备份旧版本
cd /opt
mv crypto-monitor-bot crypto-monitor-bot.backup.$(date +%Y%m%d_%H%M%S)

# 2. 解压新代码
mkdir -p crypto-monitor-bot
tar -xzf /root/crypto-bot-optimized.tar.gz -C /opt/crypto-monitor-bot/

# 3. 恢复配置文件（密码已修复）
cd /opt/crypto-monitor-bot
cat > .env << 'ENV_EOF'
TELEGRAM_BOT_TOKEN=8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68
TELEGRAM_CHAT_ID=6954384980
DATABASE_URL=postgresql://cryptobot:P%40ssw0rd2024%21Crypto%23DB@localhost:5432/crypto_monitor
REDIS_PASSWORD=R3dis$Secure#2024Pass!
REDIS_URL=redis://:R3dis%24Secure%232024Pass%21@localhost:6379/0
LOG_LEVEL=INFO
ENV_EOF

chmod 600 .env

# 4. 安装依赖
source venv/bin/activate
pip install -q -r requirements.txt

# 5. 测试运行（10秒）
echo "🧪 测试运行..."
timeout 10 venv/bin/python3 main.py || true

echo ""
echo "✅ 如果看到以下输出说明成功："
echo "   ✓ Selected XX symbols"
echo "   ✓ Subscribed to XX symbols"
echo "   ✓ Bot is running!"
echo ""

# 6. 重启服务
supervisorctl restart crypto-monitor-bot

# 7. 查看状态
echo "📊 服务状态:"
supervisorctl status crypto-monitor-bot

echo ""
echo "📝 查看实时日志:"
echo "tail -f /var/log/crypto-monitor-bot.log"
DEPLOY_COMMANDS

echo ""
echo "-------- 命令结束 --------"
echo ""

# 清理本地打包文件
rm crypto-bot-optimized.tar.gz

echo "💡 提示: 如果SSH失败，请使用腾讯云网页终端"
echo "   https://console.cloud.tencent.com/lighthouse/instance"
echo ""
