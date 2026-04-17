# 🎯 最佳方案：GitHub 一键部署

## ✅ 优势
- ✅ 无需手动上传文件
- ✅ 无需处理 SSH 密码问题
- ✅ 一行命令完成部署
- ✅ 方便版本管理和回滚

---

## 📦 步骤 1: 提交代码到 GitHub（本地执行）

```bash
# 1. 添加所有新文件
git add .

# 2. 提交（包含统一版本）
git commit -m "feat: v2.0-unified-200 - 升级到200币种监控

主要更新:
- 监控币种从50扩大到200
- 优化检测阈值（减少误报）
- 保留 Lana 交易引擎集成
- 完整测试套件
- 自动化部署工具

详见: CHANGELOG.md"

# 3. 推送到 GitHub
git push origin main
```

---

## 🖥️ 步骤 2: 服务器端部署（一行命令）

在腾讯云 Web 终端执行：

```bash
cd /root && \
[ -d crypto-monitor-bot ] && (cd crypto-monitor-bot && git pull) || \
git clone https://github.com/WEIII2020/crypto-monitor-bot.git && \
cd crypto-monitor-bot && \
python3 -m venv venv && \
source venv/bin/activate && \
pip install -r requirements.txt && \
echo "✅ v2.0-unified-200 部署完成！"
```

**这一条命令会自动：**
1. 克隆或更新代码
2. 创建虚拟环境
3. 安装依赖
4. 完成！

---

## 🎯 详细步骤

### 步骤 2.1: 打开腾讯云 Web 终端

1. 访问: https://console.cloud.tencent.com/cvm
2. 找到服务器 119.28.43.237
3. 点击 "登录" → "标准登录"

### 步骤 2.2: 执行部署命令

复制粘贴上面的一行命令，回车执行。

### 步骤 2.3: 配置环境变量

```bash
cd /root/crypto-monitor-bot

# 如果是首次部署
cp .env.example .env
vim .env
# 填入你的配置（数据库、Telegram等）
```

### 步骤 2.4: 启动服务

```bash
./start.sh
```

### 步骤 2.5: 查看日志

```bash
tail -f logs/crypto_monitor_*.log
```

应该看到：
```
✅ Selected 200 symbols
✅ Bot is running!
```

---

## 📊 验证部署

```bash
# 检查配置
cat config.yaml | grep max_count
# 应该显示: max_count: 200

# 检查进程
ps aux | grep python | grep main.py

# 查看实时日志
tail -f logs/crypto_monitor_*.log
```

---

## 🔄 后续更新

以后更新代码更简单：

```bash
cd /root/crypto-monitor-bot
git pull
source venv/bin/activate
pip install -r requirements.txt
./check_bot_status.sh restart
```

---

## 💡 为什么这个方案最好？

1. **无需密码** - 使用公开的 GitHub 仓库
2. **一行命令** - 自动化所有步骤
3. **可追溯** - Git 版本管理
4. **易回滚** - 出问题可以 `git checkout` 回退
5. **团队协作** - 多人可以共同维护

---

## 🚀 立即开始

### 在本地终端执行（提交代码）：
```bash
git add .
git commit -m "feat: v2.0-unified-200"
git push origin main
```

### 在腾讯云 Web 终端执行（部署）：
```bash
cd /root && \
[ -d crypto-monitor-bot ] && (cd crypto-monitor-bot && git pull) || \
git clone https://github.com/WEIII2020/crypto-monitor-bot.git && \
cd crypto-monitor-bot && \
python3 -m venv venv && \
source venv/bin/activate && \
pip install -r requirements.txt && \
echo "✅ 部署完成！"
```

**搞定！** 🎉
