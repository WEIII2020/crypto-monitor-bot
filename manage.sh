#!/bin/bash

# Crypto Monitor Bot - 服务管理脚本
# 使用方法: ./manage.sh [start|stop|restart|status|logs|update]

SERVICE_NAME="crypto-monitor-bot"
DEPLOY_DIR="/root/crypto-monitor-bot"
LOG_FILE="$DEPLOY_DIR/logs/bot.log"
ERROR_LOG="$DEPLOY_DIR/logs/bot.error.log"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 启动服务
start() {
    info "启动 Crypto Monitor Bot..."
    systemctl start $SERVICE_NAME

    sleep 2
    if systemctl is-active --quiet $SERVICE_NAME; then
        info "✅ 服务启动成功"
        status
    else
        error "❌ 服务启动失败"
        systemctl status $SERVICE_NAME
        exit 1
    fi
}

# 停止服务
stop() {
    info "停止 Crypto Monitor Bot..."
    systemctl stop $SERVICE_NAME

    sleep 2
    if ! systemctl is-active --quiet $SERVICE_NAME; then
        info "✅ 服务已停止"
    else
        error "❌ 服务停止失败"
        exit 1
    fi
}

# 重启服务
restart() {
    info "重启 Crypto Monitor Bot..."
    systemctl restart $SERVICE_NAME

    sleep 2
    if systemctl is-active --quiet $SERVICE_NAME; then
        info "✅ 服务重启成功"
        status
    else
        error "❌ 服务重启失败"
        systemctl status $SERVICE_NAME
        exit 1
    fi
}

# 查看状态
status() {
    echo ""
    echo "=========================================="
    echo "📊 Crypto Monitor Bot 状态"
    echo "=========================================="

    # 服务状态
    if systemctl is-active --quiet $SERVICE_NAME; then
        info "服务状态: 🟢 运行中"
    else
        warn "服务状态: 🔴 已停止"
    fi

    # 进程信息
    PID=$(pgrep -f "main_phase2.py" | head -1)
    if [ -n "$PID" ]; then
        info "进程 PID: $PID"

        # CPU 和内存
        CPU=$(ps -p $PID -o %cpu= | xargs)
        MEM=$(ps -p $PID -o %mem= | xargs)
        RSS=$(ps -p $PID -o rss= | xargs)
        RSS_MB=$((RSS / 1024))

        info "CPU 使用: ${CPU}%"
        info "内存使用: ${MEM}% (${RSS_MB}MB)"
    else
        warn "进程未运行"
    fi

    # 运行时长
    UPTIME=$(systemctl show $SERVICE_NAME --property=ActiveEnterTimestamp --value)
    if [ -n "$UPTIME" ] && [ "$UPTIME" != "n/a" ]; then
        info "运行时长: $(systemctl show $SERVICE_NAME --property=ExecMainStartTimestamp --value | xargs -I {} date -d {} '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo '未知')"
    fi

    # 日志文件大小
    if [ -f "$LOG_FILE" ]; then
        LOG_SIZE=$(du -sh "$LOG_FILE" | cut -f1)
        info "日志大小: $LOG_SIZE"
    fi

    echo "=========================================="
    echo ""
}

# 查看日志
logs() {
    TYPE=${1:-normal}
    LINES=${2:-50}

    case $TYPE in
        error)
            info "查看错误日志（最近 $LINES 行）..."
            tail -n $LINES "$ERROR_LOG"
            ;;
        follow)
            info "实时跟踪日志（Ctrl+C 退出）..."
            tail -f "$LOG_FILE"
            ;;
        signal)
            info "查看交易信号..."
            grep "NEW SIGNAL" "$LOG_FILE" | tail -n 10
            ;;
        stats)
            info "查看统计信息..."
            grep "Phase 2 Stats" "$LOG_FILE" | tail -n 10
            ;;
        *)
            info "查看普通日志（最近 $LINES 行）..."
            tail -n $LINES "$LOG_FILE"
            ;;
    esac
}

# 更新代码
update() {
    info "更新代码..."

    # 停止服务
    stop

    # 备份当前版本
    BACKUP_DIR="$DEPLOY_DIR/backups"
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/backup-$(date +%Y%m%d-%H%M%S).tar.gz"

    info "创建备份: $BACKUP_FILE"
    tar -czf "$BACKUP_FILE" \
        --exclude='venv' \
        --exclude='logs' \
        --exclude='*.pyc' \
        -C "$DEPLOY_DIR" .

    # 拉取最新代码（如果使用 git）
    if [ -d "$DEPLOY_DIR/.git" ]; then
        info "从 git 拉取最新代码..."
        cd "$DEPLOY_DIR"
        git pull
    else
        warn "未检测到 git 仓库，请手动上传代码"
        warn "使用: rsync -avz ./ root@server:$DEPLOY_DIR/"
        return 1
    fi

    # 更新依赖
    info "更新 Python 依赖..."
    source "$DEPLOY_DIR/venv/bin/activate"
    pip install -r "$DEPLOY_DIR/requirements.txt" -q -i https://pypi.tuna.tsinghua.edu.cn/simple

    # 重启服务
    start

    info "✅ 更新完成"
}

# 清理日志
clean() {
    info "清理日志文件..."

    read -p "确认清理所有日志? (yes/no): " confirm
    if [ "$confirm" = "yes" ]; then
        > "$LOG_FILE"
        > "$ERROR_LOG"
        info "✅ 日志已清理"
    else
        warn "已取消"
    fi
}

# 诊断
diagnose() {
    echo ""
    echo "=========================================="
    echo "🔍 系统诊断"
    echo "=========================================="

    # 检查服务状态
    info "1. 服务状态"
    systemctl is-active --quiet $SERVICE_NAME && echo "  ✅ 服务运行中" || echo "  ❌ 服务未运行"

    # 检查进程
    info "2. 进程检查"
    pgrep -f "main_phase2.py" > /dev/null && echo "  ✅ 进程存在" || echo "  ❌ 进程不存在"

    # 检查配置文件
    info "3. 配置文件"
    [ -f "$DEPLOY_DIR/config/config.yaml" ] && echo "  ✅ config.yaml 存在" || echo "  ❌ config.yaml 不存在"
    [ -f "$DEPLOY_DIR/.env" ] && echo "  ✅ .env 存在" || echo "  ⚠️  .env 不存在"

    # 检查日志
    info "4. 最近错误"
    ERROR_COUNT=$(grep -c "ERROR" "$LOG_FILE" 2>/dev/null || echo 0)
    echo "  错误数量: $ERROR_COUNT"
    if [ "$ERROR_COUNT" -gt 0 ]; then
        grep "ERROR" "$LOG_FILE" | tail -n 5
    fi

    # 检查网络
    info "5. 网络连接"
    curl -s -o /dev/null -w "%{http_code}" https://api.binance.com/api/v3/ping | grep -q 200 && \
        echo "  ✅ Binance API 可访问" || echo "  ❌ Binance API 不可访问"

    # 检查资源
    info "6. 系统资源"
    echo "  磁盘空间: $(df -h / | awk 'NR==2 {print $4}') 可用"
    echo "  内存使用: $(free -h | awk 'NR==2 {print $3 "/" $2}')"

    echo "=========================================="
    echo ""
}

# 帮助信息
help() {
    cat << EOF
Crypto Monitor Bot - 服务管理脚本

使用方法:
  ./manage.sh [命令] [选项]

命令:
  start       启动服务
  stop        停止服务
  restart     重启服务
  status      查看状态
  logs        查看日志
    - logs [normal|error|follow|signal|stats] [行数]
  update      更新代码
  clean       清理日志
  diagnose    系统诊断
  help        显示帮助

示例:
  ./manage.sh start            # 启动服务
  ./manage.sh logs follow      # 实时查看日志
  ./manage.sh logs error 100   # 查看最近 100 行错误日志
  ./manage.sh logs signal      # 查看交易信号
  ./manage.sh update           # 更新代码

EOF
}

# 主逻辑
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs "$2" "$3"
        ;;
    update)
        update
        ;;
    clean)
        clean
        ;;
    diagnose)
        diagnose
        ;;
    help|--help|-h)
        help
        ;;
    *)
        error "无效的命令: $1"
        echo ""
        help
        exit 1
        ;;
esac
