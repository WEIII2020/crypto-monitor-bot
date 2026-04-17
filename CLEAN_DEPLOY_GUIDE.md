# 🎯 清理并重新部署 v2.0-unified-200

## 📋 概览

这个过程分为 3 个阶段：
1. **在腾讯云服务器上清理旧文件**
2. **从本地上传新版本**
3. **在服务器上部署新版本**

---

## 🖥️ 阶段 1: 服务器清理

### 在腾讯云 Web 终端执行：

```bash
# 1. 执行清理（复制整段）
cd /root && pkill -f "python.*main.py" && sleep 2 && \
rm -f crypto-bot-*.tar.gz && \
rm -rf crypto-bot-200symbols crypto-bot-lana-optimized crypto-bot-lana-fixed crypto-bot-optimized crypto-monitor-bot && \
rm -f check-all.sh deploy.sh optimize_hermes.sh setup_git.sh && \
echo "✅ 清理完成！" && \
echo "" && \
echo "📊 保留的文件：" && \
ls -lah | grep -E "hermes|\.sh"
```

---

## 📤 阶段 2: 上传新版本

### 方法 A: 使用 SCP（如果密码可用）

**在本地终端执行：**

```bash
scp /tmp/crypto-monitor-bot-v2.0-unified.tar.gz root@119.28.43.237:/root/
```

### 方法 B: 使用 Cyberduck（推荐）

1. 打开 Cyberduck
2. 连接到服务器（SFTP）
   - 地址: `119.28.43.237`
   - 用户: `root`
   - 端口: `22`
3. 上传文件：
   - 本地文件: `/tmp/crypto-monitor-bot-v2.0-unified.tar.gz`
   - 服务器位置: `/root/`

### 方法 C: 腾讯云 Web 终端上传

1. 在腾讯云控制台的 Web 终端
2. 找到顶部的 "文件传输" 或 "上传" 按钮
3. 选择本地文件: `/tmp/crypto-monitor-bot-v2.0-unified.tar.gz`
4. 上传到 `/root/`

---

## 🚀 阶段 3: 服务器部署

### 在腾讯云 Web 终端执行：

```bash
# 1. 验证文件已上传
ls -lh /root/crypto-monitor-bot-v2.0-unified.tar.gz

# 2. 解压和部署（复制整段）
cd /root && \
mkdir -p crypto-monitor-bot && \
tar -xzf crypto-monitor-bot-v2.0-unified.tar.gz -C crypto-monitor-bot/ && \
cd crypto-monitor-bot && \
if [ -f /root/hermes.env ]; then cp /root/hermes.env .env; fi && \
python3 -m venv venv && \
source venv/bin/activate && \
pip install -q --upgrade pip && \
pip install -q -r requirements.txt && \
echo "✅ 部署完成！"

# 3. 验证配置
grep "max_count" config.yaml
grep "max_symbols" main.py

# 4. 启动服务
nohup python main.py > bot.log 2>&1 &
echo $! > bot.pid

# 5. 等待并查看日志
sleep 5
tail -50 bot.log
```

---

## ✅ 验证成功

在日志中应该看到：

```
✅ Selected 200 symbols
   Preview: BTCUSDT, ETHUSDT, BNBUSDT, ...
✅ Bot is running!
```

---

## 📝 后续管理

### 查看实时日志
```bash
cd /root/crypto-monitor-bot
tail -f bot.log
```

### 检查进程
```bash
ps aux | grep python | grep main.py
```

### 停止服务
```bash
pkill -f "python.*main.py"
```

### 重启服务
```bash
cd /root/crypto-monitor-bot
source venv/bin/activate
nohup python main.py > bot.log 2>&1 &
```

---

## 📁 文件结构（清理后）

```
/root/
├── .hermes/                              # Hermes Agent（保留）
├── crypto-monitor-bot/                   # 新的 v2.0
│   ├── main.py
│   ├── config.yaml
│   ├── .env
│   ├── venv/
│   └── src/
├── crypto-monitor-bot-v2.0-unified.tar.gz # 压缩包
├── hermes.env                            # 环境配置（保留）
├── start-hermes.sh                       # Hermes 脚本（保留）
├── stop-hermes.sh
├── restart-hermes.sh
└── logs-hermes.sh
```

---

## 🎉 完成！

现在你有了一个干净的 v2.0-unified-200 版本，监控 200 个币种！
