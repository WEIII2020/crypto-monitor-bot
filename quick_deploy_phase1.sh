#!/bin/bash
# Phase 1 快速部署脚本

set -e  # 遇到错误立即退出

echo "🚀 Phase 1 - 毫秒级实时监控部署"
echo "=================================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查当前目录
if [ ! -f "main.py" ]; then
    echo -e "${RED}❌ 错误: 请在项目根目录运行此脚本${NC}"
    exit 1
fi

echo -e "${YELLOW}📦 Step 1: 安装依赖${NC}"
echo "-----------------------------------"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

source venv/bin/activate

# 安装 numpy（新依赖）
echo "安装 numpy..."
pip install -q numpy

echo -e "${GREEN}✅ 依赖安装完成${NC}"
echo ""

echo -e "${YELLOW}🧪 Step 2: 运行测试（可选）${NC}"
echo "-----------------------------------"
read -p "是否运行性能测试？(y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "运行测试套件..."
    python tests/test_realtime_system.py
    echo ""
fi

echo -e "${YELLOW}🎯 Step 3: 选择运行模式${NC}"
echo "-----------------------------------"
echo "1) 测试模式（5个币种，快速验证）"
echo "2) 生产模式（200个币种，完整监控）"
read -p "请选择 (1/2): " -n 1 -r
echo

if [[ $REPLY == "1" ]]; then
    MODE="test"
    echo "📌 已选择：测试模式"

    # 修改 main_realtime.py 开启测试模式
    sed -i.bak 's/test_mode = False/test_mode = True/' main_realtime.py

elif [[ $REPLY == "2" ]]; then
    MODE="production"
    echo "📌 已选择：生产模式"

    # 修改 main_realtime.py 关闭测试模式
    sed -i.bak 's/test_mode = True/test_mode = False/' main_realtime.py
else
    echo -e "${RED}❌ 无效选择，退出${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}🚀 Step 4: 启动实时监控${NC}"
echo "-----------------------------------"

# 停止旧进程
if [ -f "bot_realtime.pid" ]; then
    OLD_PID=$(cat bot_realtime.pid)
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "停止旧进程 (PID: $OLD_PID)..."
        kill $OLD_PID
        sleep 2
    fi
fi

# 启动新进程
if [[ $MODE == "test" ]]; then
    LOG_FILE="bot_realtime_test.log"
else
    LOG_FILE="bot_realtime.log"
fi

echo "启动实时监控..."
nohup python main_realtime.py > $LOG_FILE 2>&1 &
NEW_PID=$!
echo $NEW_PID > bot_realtime.pid

echo -e "${GREEN}✅ 已启动 (PID: $NEW_PID)${NC}"
echo ""

echo -e "${YELLOW}⏳ 等待启动...${NC}"
sleep 5

echo ""
echo -e "${YELLOW}📊 Step 5: 验证运行状态${NC}"
echo "-----------------------------------"

# 检查进程
if ps -p $NEW_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✅ 进程运行正常 (PID: $NEW_PID)${NC}"
else
    echo -e "${RED}❌ 进程启动失败，查看日志:${NC}"
    tail -20 $LOG_FILE
    exit 1
fi

# 显示日志
echo ""
echo "最新日志（前30行）："
echo "-----------------------------------"
tail -30 $LOG_FILE

echo ""
echo "=================================="
echo -e "${GREEN}🎉 Phase 1 部署完成！${NC}"
echo "=================================="
echo ""
echo "📋 管理命令："
echo "  查看实时日志:   tail -f $LOG_FILE"
echo "  查看性能统计:   tail -f $LOG_FILE | grep Performance"
echo "  停止服务:       kill $NEW_PID"
echo "  重启服务:       ./quick_deploy_phase1.sh"
echo ""
echo "📊 预期输出："
if [[ $MODE == "test" ]]; then
    echo "  - 监控币种: 5"
    echo "  - 交易笔数: 50-100 trades/s"
else
    echo "  - 监控币种: 200"
    echo "  - 交易笔数: 100-200 trades/s"
fi
echo "  - 平均延迟: 20-50ms"
echo ""
echo -e "${YELLOW}💡 提示: 如果看到 '📊 Performance' 输出，说明系统运行正常！${NC}"
echo ""
