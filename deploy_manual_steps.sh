#!/bin/bash
# 手动部署步骤 - 适用于需要密码的服务器

VERSION="v2.0-unified-200"
SERVER_IP="119.28.43.237"
PACKAGE_NAME="crypto-bot-${VERSION}-$(date +%Y%m%d-%H%M%S).tar.gz"

echo "🎯 手动部署指南"
echo "==============================================="
echo ""
echo "📦 步骤 1: 打包代码（本地）"
echo "-----------------------------------------------"
echo "执行命令："
echo ""
cat << 'CMD'
tar -czf /tmp/crypto-bot-v2.0.tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='hermes_server_code' \
  --exclude='*.log' \
  --exclude='.env' \
  --exclude='logs/*.zip' \
  .
CMD
echo ""
echo "执行中..."
tar -czf /tmp/crypto-bot-v2.0.tar.gz \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='hermes_server_code' \
  --exclude='*.log' \
  --exclude='.env' \
  --exclude='logs/*.zip' \
  .

if [ -f "/tmp/crypto-bot-v2.0.tar.gz" ]; then
    SIZE=$(du -h /tmp/crypto-bot-v2.0.tar.gz | cut -f1)
    echo "✅ 打包完成: /tmp/crypto-bot-v2.0.tar.gz"
    echo "   大小: ${SIZE}"
else
    echo "❌ 打包失败"
    exit 1
fi

echo ""
echo "📤 步骤 2: 上传到服务器"
echo "-----------------------------------------------"
echo "执行以下命令（会提示输入密码）："
echo ""
echo "scp /tmp/crypto-bot-v2.0.tar.gz root@${SERVER_IP}:/root/"
echo ""
echo "按回车继续上传..."
read

scp /tmp/crypto-bot-v2.0.tar.gz root@${SERVER_IP}:/root/

if [ $? -eq 0 ]; then
    echo "✅ 上传成功"
else
    echo "❌ 上传失败，请检查网络和密码"
    exit 1
fi

echo ""
echo "🖥️  步骤 3: 在服务器上部署"
echo "-----------------------------------------------"
echo "现在需要 SSH 登录到服务器执行部署命令"
echo ""
echo "请复制以下命令，然后执行 ssh root@${SERVER_IP}"
echo ""
echo "==============================================="
echo "# === 在服务器上执行以下命令 ==="
echo ""
cat << 'SERVERCMD'
# 1. 备份旧版本
if [ -d "/root/crypto-monitor-bot" ]; then
    echo "🔄 备份旧版本..."
    mkdir -p /root/backups
    BACKUP_NAME="crypto-bot-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
    cd /root
    tar -czf backups/${BACKUP_NAME} crypto-monitor-bot
    echo "✅ 备份完成: backups/${BACKUP_NAME}"
    
    # 保存 .env
    if [ -f "/root/crypto-monitor-bot/.env" ]; then
        cp /root/crypto-monitor-bot/.env /tmp/.env.backup
        echo "✅ 已保存 .env 配置"
    fi
fi

# 2. 清理并解压新版本
echo "📦 部署新版本..."
rm -rf /root/crypto-monitor-bot
mkdir -p /root/crypto-monitor-bot
tar -xzf /root/crypto-bot-v2.0.tar.gz -C /root/crypto-monitor-bot

# 3. 恢复 .env
if [ -f "/tmp/.env.backup" ]; then
    mv /tmp/.env.backup /root/crypto-monitor-bot/.env
    echo "✅ 恢复 .env 配置"
else
    echo "⚠️  创建新的 .env 文件"
    cp /root/crypto-monitor-bot/.env.example /root/crypto-monitor-bot/.env
    echo "⚠️  请编辑 /root/crypto-monitor-bot/.env 填入配置"
fi

# 4. 设置权限
cd /root/crypto-monitor-bot
chmod +x *.sh 2>/dev/null || true

# 5. 创建虚拟环境
echo "📦 创建Python虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 6. 安装依赖
echo "📦 安装依赖包..."
pip install --upgrade pip
pip install -r requirements.txt

echo ""
echo "✅ 部署完成！"
echo ""
echo "版本: v2.0-unified-200"
echo "监控币种: 200 个"
echo ""
echo "📝 下一步:"
echo "1. 检查配置: cat config.yaml | grep max_count"
echo "2. 编辑 .env: vim .env"
echo "3. 启动服务: ./start.sh"
echo "4. 查看日志: tail -f logs/crypto_monitor_*.log"

SERVERCMD

echo "==============================================="
echo ""
echo "现在请 SSH 登录服务器并执行上述命令："
echo ""
echo "ssh root@${SERVER_IP}"
echo ""
echo "提示: 你可以直接复制粘贴所有命令一次性执行"

