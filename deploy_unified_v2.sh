#!/bin/bash
# Hermes Bot v2.0 统一版本部署脚本
# 用途：将本地优化版本部署到腾讯云服务器

set -e  # Exit on error

# ============================================
# 配置变量
# ============================================
VERSION="v2.0-unified-200"
SERVER_IP="119.28.43.237"
SERVER_USER="root"
SERVER_PORT="22"
REMOTE_DIR="/root/crypto-monitor-bot"
BACKUP_DIR="/root/backups"

# 颜色输出
RED='\033[0.31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================
# 辅助函数
# ============================================
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================
# 1. 打包本地代码
# ============================================
log_info "步骤 1/6: 打包本地代码..."

# 创建临时目录
TMP_DIR=$(mktemp -d)
PACKAGE_NAME="crypto-bot-${VERSION}-$(date +%Y%m%d-%H%M%S).tar.gz"

# 复制文件到临时目录（排除不需要的文件）
rsync -av \
  --exclude='venv' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='hermes_server_code' \
  --exclude='*.log' \
  --exclude='.env' \
  . "$TMP_DIR/"

# 打包
cd "$TMP_DIR"
tar -czf "/tmp/${PACKAGE_NAME}" .
cd - > /dev/null

log_info "✅ 打包完成: /tmp/${PACKAGE_NAME}"
log_info "   大小: $(du -h /tmp/${PACKAGE_NAME} | cut -f1)"

# ============================================
# 2. 连接测试
# ============================================
log_info "步骤 2/6: 测试服务器连接..."

if ssh -p ${SERVER_PORT} -o ConnectTimeout=10 ${SERVER_USER}@${SERVER_IP} "echo '连接成功'" &>/dev/null; then
    log_info "✅ 服务器连接正常"
else
    log_error "❌ 无法连接到服务器 ${SERVER_IP}"
    log_error "   请检查: 1) 网络连接 2) SSH密钥/密码 3) 服务器IP"
    exit 1
fi

# ============================================
# 3. 备份服务器现有代码
# ============================================
log_info "步骤 3/6: 备份服务器现有代码..."

ssh -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
    # 创建备份目录
    mkdir -p /root/backups
    
    # 如果存在旧代码，则备份
    if [ -d "/root/crypto-monitor-bot" ]; then
        BACKUP_NAME="crypto-bot-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
        cd /root
        tar -czf backups/${BACKUP_NAME} crypto-monitor-bot
        echo "✅ 备份完成: backups/${BACKUP_NAME}"
    else
        echo "⚠️  未发现旧版本，跳过备份"
    fi
ENDSSH

# ============================================
# 4. 上传新版本
# ============================================
log_info "步骤 4/6: 上传新版本到服务器..."

scp -P ${SERVER_PORT} "/tmp/${PACKAGE_NAME}" ${SERVER_USER}@${SERVER_IP}:/root/
log_info "✅ 上传完成"

# ============================================
# 5. 服务器端部署
# ============================================
log_info "步骤 5/6: 在服务器上部署..."

ssh -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP} << ENDSSH
    set -e
    
    # 停止旧服务
    if [ -f "/root/crypto-monitor-bot/stop.sh" ]; then
        echo "🛑 停止旧服务..."
        cd /root/crypto-monitor-bot
        ./stop.sh || true
    fi
    
    # 清理旧代码（保留 .env）
    if [ -d "/root/crypto-monitor-bot" ]; then
        cp /root/crypto-monitor-bot/.env /tmp/.env.backup 2>/dev/null || true
        rm -rf /root/crypto-monitor-bot
    fi
    
    # 解压新版本
    echo "📦 解压新版本..."
    mkdir -p /root/crypto-monitor-bot
    tar -xzf /root/${PACKAGE_NAME} -C /root/crypto-monitor-bot
    
    # 恢复 .env
    if [ -f "/tmp/.env.backup" ]; then
        mv /tmp/.env.backup /root/crypto-monitor-bot/.env
        echo "✅ 恢复环境变量配置"
    else
        echo "⚠️  未发现 .env 文件，请手动创建"
        cp /root/crypto-monitor-bot/.env.example /root/crypto-monitor-bot/.env
    fi
    
    # 设置权限
    cd /root/crypto-monitor-bot
    chmod +x *.sh 2>/dev/null || true
    
    # 创建虚拟环境并安装依赖
    echo "📦 安装Python依赖..."
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    echo "✅ 部署完成！"
    echo ""
    echo "版本信息: ${VERSION}"
    echo "部署时间: $(date)"
ENDSSH

# ============================================
# 6. 验证部署
# ============================================
log_info "步骤 6/6: 验证部署..."

ssh -p ${SERVER_PORT} ${SERVER_USER}@${SERVER_IP} << 'ENDSSH'
    cd /root/crypto-monitor-bot
    
    echo "📊 目录结构:"
    ls -lh
    
    echo ""
    echo "📦 Python包:"
    source venv/bin/activate
    pip list | grep -E "ccxt|websockets|asyncpg|redis|python-telegram-bot"
    
    echo ""
    echo "✅ 验证完成！"
ENDSSH

# ============================================
# 清理
# ============================================
rm -rf "$TMP_DIR"
rm -f "/tmp/${PACKAGE_NAME}"

log_info ""
log_info "🎉 部署成功完成！"
log_info ""
log_info "下一步操作:"
log_info "1. SSH登录服务器: ssh ${SERVER_USER}@${SERVER_IP}"
log_info "2. 进入目录: cd /root/crypto-monitor-bot"
log_info "3. 检查配置: vim .env"
log_info "4. 启动服务: ./start.sh"
log_info "5. 查看日志: ./logs.sh"
log_info ""
log_info "📝 备份位置: ${SERVER_IP}:/root/backups/"
log_info "📦 版本: ${VERSION}"
