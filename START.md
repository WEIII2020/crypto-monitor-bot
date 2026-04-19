# 🚀 立即开始

## 快速启动（3步）

### 步骤 1: 确保虚拟环境已创建

```bash
# 如果还没有虚拟环境
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 步骤 2: 配置 Telegram（可选）

```bash
# 编辑 .env 文件
vim .env

# 添加以下内容
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

**获取 Token 和 Chat ID：**
- Bot Token: Telegram 搜索 `@BotFather`，发送 `/newbot`
- Chat ID: Telegram 搜索 `@userinfobot`，发送任意消息

### 步骤 3: 启动系统

```bash
# 使用交互式启动脚本（推荐）
./start_now.sh

# 或直接启动信号模式
./run.sh signal

# 或启动统一模式（监控 + Hermes Agent）
./run_unified.sh signal
```

---

## 运行模式对比

| 模式 | 命令 | 功能 |
|------|------|------|
| **Monitor** | `./start_now.sh` → 选择 1 | 只采集数据 |
| **Signal** ⭐ | `./start_now.sh` → 选择 2 | 采集 + 信号生成（默认）|
| **Unified** | `./start_now.sh` → 选择 3 | 完整功能 + Hermes Agent |
| **Trade** ⚠️ | `./start_now.sh` → 选择 4 | 自动交易模式 |

---

## 查看运行状态

```bash
# 查看实时日志
tail -f logs/monitor.log

# 查看最近的信号
grep "NEW SIGNAL" logs/monitor.log | tail -10

# 查看系统状态
./manage.sh status

# 查看统计信息
./manage.sh stats
```

---

## 测试 Hermes Agent（统一模式）

启动统一模式后，打开 Telegram 发送命令：

```
/status     # 查看系统状态
/signals    # 查看最近信号
/help       # 查看所有命令
```

---

## 常见问题

### Q: 没有虚拟环境？

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Q: 缺少依赖？

```bash
source venv/bin/activate
pip install loguru pyyaml aiohttp -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q: 没有收到 Telegram 通知？

1. 检查 `.env` 文件是否配置正确
2. 测试 Bot Token：
   ```bash
   python3 -c "from telegram import Bot; print(Bot('YOUR_TOKEN').get_me())"
   ```

### Q: 如何停止系统？

```bash
# 前台运行：按 Ctrl+C
# 后台运行：
./manage.sh stop
# 或
pkill -f main_phase2.py
```

---

## 📚 完整文档

- `QUICKSTART.md` - 快速开始
- `MERGE_COMPLETE.md` - 合并说明
- `README_MERGED.md` - 完整功能
- `DEPLOYMENT_GUIDE.md` - 部署指南

---

## 🎉 开始使用

```bash
./start_now.sh
```

**祝您使用愉快！**
