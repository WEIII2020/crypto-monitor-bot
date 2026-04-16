#!/bin/bash
#
# 腾讯云自动部署脚本
# Crypto Monitor Bot - Tencent Cloud Deployment
#
# 使用方法:
#   bash deploy_tencent_cloud.sh
#

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""
}

# 检查是否以 root 运行
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "请使用 root 权限运行此脚本"
        print_info "使用: sudo bash deploy_tencent_cloud.sh"
        exit 1
    fi
}

# 检查操作系统
check_os() {
    print_header "检查操作系统"

    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
        print_info "检测到操作系统: $OS $VER"

        if [[ "$OS" != *"Ubuntu"* ]]; then
            print_warning "此脚本针对 Ubuntu 优化，其他系统可能需要调整"
            read -p "是否继续? (y/n): " continue
            if [[ "$continue" != "y" ]]; then
                exit 0
            fi
        fi
    else
        print_warning "无法检测操作系统版本"
    fi

    print_success "操作系统检查完成"
}

# 更新系统
update_system() {
    print_header "更新系统软件包"

    print_info "正在更新软件包列表..."
    apt update -y

    print_info "正在升级已安装的软件包..."
    apt upgrade -y

    print_success "系统更新完成"
}

# 安装基础依赖
install_dependencies() {
    print_header "安装基础依赖"

    print_info "安装 Python 3.9+..."
    apt install -y python3.9 python3.9-venv python3-pip

    print_info "安装 PostgreSQL..."
    apt install -y postgresql postgresql-contrib

    print_info "安装 Redis..."
    apt install -y redis-server

    print_info "安装 Git..."
    apt install -y git

    print_info "安装 Supervisor..."
    apt install -y supervisor

    print_info "安装系统工具..."
    apt install -y htop curl wget vim net-tools

    print_success "依赖安装完成"
}

# 配置 PostgreSQL
configure_postgresql() {
    print_header "配置 PostgreSQL 数据库"

    # 读取配置
    read -p "请输入 PostgreSQL 用户名 [cryptobot]: " pg_user
    pg_user=${pg_user:-cryptobot}

    read -sp "请输入 PostgreSQL 密码: " pg_password
    echo ""

    if [ -z "$pg_password" ]; then
        print_error "密码不能为空"
        exit 1
    fi

    read -p "请输入数据库名 [crypto_monitor]: " pg_db
    pg_db=${pg_db:-crypto_monitor}

    print_info "创建数据库用户和数据库..."

    # 创建用户和数据库
    sudo -u postgres psql <<EOF
CREATE USER $pg_user WITH PASSWORD '$pg_password';
CREATE DATABASE $pg_db OWNER $pg_user;
GRANT ALL PRIVILEGES ON DATABASE $pg_db TO $pg_user;
EOF

    print_info "配置 PostgreSQL 访问权限..."
    echo "host    all             all             127.0.0.1/32            md5" >> /etc/postgresql/*/main/pg_hba.conf

    print_info "重启 PostgreSQL..."
    systemctl restart postgresql
    systemctl enable postgresql

    # 保存配置到全局变量
    export PG_USER=$pg_user
    export PG_PASSWORD=$pg_password
    export PG_DB=$pg_db

    print_success "PostgreSQL 配置完成"
}

# 配置 Redis
configure_redis() {
    print_header "配置 Redis"

    read -sp "请输入 Redis 密码: " redis_password
    echo ""

    if [ -z "$redis_password" ]; then
        print_error "密码不能为空"
        exit 1
    fi

    print_info "配置 Redis 密码..."

    # 备份原配置
    cp /etc/redis/redis.conf /etc/redis/redis.conf.backup

    # 设置密码
    sed -i "s/# requirepass foobared/requirepass $redis_password/" /etc/redis/redis.conf

    # 确保只监听本地
    sed -i "s/bind 127.0.0.1/bind 127.0.0.1/" /etc/redis/redis.conf

    print_info "重启 Redis..."
    systemctl restart redis
    systemctl enable redis

    # 保存配置
    export REDIS_PASSWORD=$redis_password

    print_success "Redis 配置完成"
}

# 部署项目
deploy_project() {
    print_header "部署项目"

    PROJECT_DIR="/opt/crypto-monitor-bot"

    print_info "创建项目目录: $PROJECT_DIR"
    mkdir -p $PROJECT_DIR
    cd $PROJECT_DIR

    # 选择获取代码的方式
    echo "请选择获取项目代码的方式:"
    echo "1) 从 Git 仓库克隆"
    echo "2) 手动上传（稍后需要使用 scp/sftp 上传）"
    read -p "选择 [1]: " deploy_method
    deploy_method=${deploy_method:-1}

    if [ "$deploy_method" = "1" ]; then
        read -p "请输入 Git 仓库地址: " git_repo

        if [ -z "$git_repo" ]; then
            print_error "Git 仓库地址不能为空"
            exit 1
        fi

        print_info "克隆代码..."
        git clone $git_repo .
    else
        print_warning "请稍后使用以下命令上传代码:"
        print_info "scp -r /local/path/crypto-monitor-bot/* root@$(curl -s ifconfig.me):$PROJECT_DIR/"
        read -p "按回车键继续（确保代码已上传）..."
    fi

    # 检查必要文件
    if [ ! -f "requirements.txt" ] || [ ! -f "main.py" ]; then
        print_error "项目文件不完整，请确保 requirements.txt 和 main.py 存在"
        exit 1
    fi

    print_info "创建 Python 虚拟环境..."
    python3.9 -m venv venv

    print_info "激活虚拟环境并安装依赖..."
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

    print_success "项目部署完成"
}

# 配置环境变量
configure_env() {
    print_header "配置环境变量"

    PROJECT_DIR="/opt/crypto-monitor-bot"
    cd $PROJECT_DIR

    # Telegram 配置
    read -p "请输入 Telegram Bot Token: " telegram_token
    if [ -z "$telegram_token" ]; then
        print_error "Telegram Bot Token 不能为空"
        exit 1
    fi

    read -p "请输入 Telegram Chat ID: " telegram_chat_id
    if [ -z "$telegram_chat_id" ]; then
        print_error "Telegram Chat ID 不能为空"
        exit 1
    fi

    # Binance API（可选）
    read -p "是否配置 Binance API？(y/n) [n]: " use_binance_api
    use_binance_api=${use_binance_api:-n}

    if [ "$use_binance_api" = "y" ]; then
        read -p "请输入 Binance API Key: " binance_api_key
        read -sp "请输入 Binance API Secret: " binance_api_secret
        echo ""
    else
        binance_api_key=""
        binance_api_secret=""
    fi

    print_info "创建 .env 文件..."

    cat > .env <<EOF
# Telegram Bot
TELEGRAM_BOT_TOKEN=$telegram_token
TELEGRAM_CHAT_ID=$telegram_chat_id

# Exchange APIs (optional)
BINANCE_API_KEY=$binance_api_key
BINANCE_API_SECRET=$binance_api_secret

# Database
POSTGRES_USER=$PG_USER
POSTGRES_PASSWORD=$PG_PASSWORD
POSTGRES_DB=$PG_DB
DATABASE_URL=postgresql://$PG_USER:$PG_PASSWORD@localhost:5432/$PG_DB

# Redis
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_URL=redis://:$REDIS_PASSWORD@localhost:6379/0

# Alert Thresholds
WARNING_THRESHOLD_5M=10.0
CRITICAL_THRESHOLD_5M=20.0
VOLUME_WARNING_MULTIPLIER=5.0
VOLUME_CRITICAL_MULTIPLIER=10.0

# Monitoring Settings
ENABLE_NIGHT_MODE=false
NIGHT_START_HOUR=23
NIGHT_END_HOUR=7

# Logging
LOG_LEVEL=INFO
EOF

    chmod 600 .env

    print_success "环境变量配置完成"
}

# 测试运行
test_run() {
    print_header "测试运行"

    PROJECT_DIR="/opt/crypto-monitor-bot"
    cd $PROJECT_DIR

    print_info "启动测试运行（15秒）..."
    print_warning "如果看到错误，请按 Ctrl+C 停止"

    timeout 15 venv/bin/python main.py || true

    echo ""
    read -p "是否看到 '✅ Bot is running!' 消息？(y/n): " test_success

    if [ "$test_success" != "y" ]; then
        print_error "测试失败，请检查配置"
        print_info "查看日志: tail -f /var/log/crypto-monitor-bot.log"
        exit 1
    fi

    print_success "测试运行成功"
}

# 配置 Supervisor
configure_supervisor() {
    print_header "配置 Supervisor（开机自启动）"

    PROJECT_DIR="/opt/crypto-monitor-bot"

    print_info "创建 Supervisor 配置文件..."

    cat > /etc/supervisor/conf.d/crypto-monitor-bot.conf <<EOF
[program:crypto-monitor-bot]
directory=$PROJECT_DIR
command=$PROJECT_DIR/venv/bin/python main.py
user=root
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/crypto-monitor-bot.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
environment=PATH="$PROJECT_DIR/venv/bin"
EOF

    print_info "重载 Supervisor 配置..."
    supervisorctl reread
    supervisorctl update

    print_info "启动服务..."
    supervisorctl start crypto-monitor-bot

    sleep 3

    print_info "检查服务状态..."
    supervisorctl status crypto-monitor-bot

    print_success "Supervisor 配置完成"
}

# 配置防火墙
configure_firewall() {
    print_header "配置防火墙（可选）"

    read -p "是否配置 UFW 防火墙？(y/n) [y]: " setup_firewall
    setup_firewall=${setup_firewall:-y}

    if [ "$setup_firewall" != "y" ]; then
        print_info "跳过防火墙配置"
        return
    fi

    print_info "安装 UFW..."
    apt install -y ufw

    print_info "配置防火墙规则..."
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp

    print_warning "即将启用防火墙，请确保 SSH 连接不会中断"
    read -p "按回车键继续..."

    ufw --force enable

    print_success "防火墙配置完成"
}

# 配置自动备份
configure_backup() {
    print_header "配置数据库自动备份（可选）"

    read -p "是否配置自动备份？(y/n) [y]: " setup_backup
    setup_backup=${setup_backup:-y}

    if [ "$setup_backup" != "y" ]; then
        print_info "跳过备份配置"
        return
    fi

    BACKUP_DIR="/opt/backups"
    mkdir -p $BACKUP_DIR

    print_info "创建备份脚本..."

    cat > /opt/backup_db.sh <<EOF
#!/bin/bash
DATE=\$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="$BACKUP_DIR"

# 备份 PostgreSQL
pg_dump -h localhost -U $PG_USER $PG_DB > \$BACKUP_DIR/db_\$DATE.sql

# 保留最近7天的备份
find \$BACKUP_DIR -name "db_*.sql" -mtime +7 -delete

echo "\$(date): Backup completed: db_\$DATE.sql" >> /var/log/backup.log
EOF

    chmod +x /opt/backup_db.sh

    print_info "配置定时任务（每天凌晨3点）..."
    (crontab -l 2>/dev/null; echo "0 3 * * * /opt/backup_db.sh") | crontab -

    print_success "自动备份配置完成"
}

# 显示部署信息
show_deployment_info() {
    print_header "部署完成！"

    SERVER_IP=$(curl -s ifconfig.me)

    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Crypto Monitor Bot 部署成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo -e "${BLUE}服务器信息:${NC}"
    echo "  公网IP: $SERVER_IP"
    echo "  项目目录: /opt/crypto-monitor-bot"
    echo ""
    echo -e "${BLUE}数据库信息:${NC}"
    echo "  PostgreSQL: localhost:5432"
    echo "  数据库名: $PG_DB"
    echo "  用户名: $PG_USER"
    echo ""
    echo -e "${BLUE}常用命令:${NC}"
    echo "  查看状态: supervisorctl status"
    echo "  查看日志: tail -f /var/log/crypto-monitor-bot.log"
    echo "  重启服务: supervisorctl restart crypto-monitor-bot"
    echo "  停止服务: supervisorctl stop crypto-monitor-bot"
    echo ""
    echo -e "${BLUE}下一步:${NC}"
    echo "  1. 查看日志确认运行正常"
    echo "  2. 在 Telegram 上测试接收告警"
    echo "  3. 根据需要调整配置文件 config.yaml"
    echo ""
    echo -e "${YELLOW}重要提醒:${NC}"
    echo "  - 定期查看日志: tail -f /var/log/crypto-monitor-bot.log"
    echo "  - 数据库备份位置: /opt/backups/"
    echo "  - 修改配置后需重启: supervisorctl restart crypto-monitor-bot"
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo ""
}

# 主函数
main() {
    clear

    echo -e "${BLUE}"
    cat << "EOF"
╔═══════════════════════════════════════════╗
║                                           ║
║   Crypto Monitor Bot                      ║
║   腾讯云自动部署脚本                       ║
║                                           ║
║   Version: 1.0.0                          ║
║                                           ║
╚═══════════════════════════════════════════╝
EOF
    echo -e "${NC}"

    print_warning "此脚本将自动完成以下操作:"
    echo "  1. 更新系统"
    echo "  2. 安装 Python、PostgreSQL、Redis 等依赖"
    echo "  3. 配置数据库"
    echo "  4. 部署项目代码"
    echo "  5. 配置开机自启动"
    echo "  6. （可选）配置防火墙和自动备份"
    echo ""

    read -p "是否继续？(y/n): " confirm
    if [ "$confirm" != "y" ]; then
        print_info "已取消部署"
        exit 0
    fi

    # 执行部署步骤
    check_root
    check_os
    update_system
    install_dependencies
    configure_postgresql
    configure_redis
    deploy_project
    configure_env
    test_run
    configure_supervisor
    configure_firewall
    configure_backup
    show_deployment_info

    print_success "所有步骤完成！"
}

# 运行主函数
main
