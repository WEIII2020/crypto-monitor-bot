# 🚀 我的部署步骤 - 腾讯云自动部署

**服务器IP**: 119.28.43.237  
**方式**: 方法A - 自动部署

---

## ✅ 第一步：获取 Telegram Chat ID（2分钟）

### 你的 Bot Token 已有：
```
8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68
```

### 获取 Chat ID：

**最简单的方法**：
1. 在 Telegram 搜索并打开 **@userinfobot**
2. 点击「START」或发送 `/start`
3. 机器人会回复类似：
   ```
   👤 First name: Lucas
   🆔 ID: 1234567890    ← 这就是你的 Chat ID
   ```
4. **复制这个数字**（例如：1234567890）

**或者浏览器方法**：
1. 先给你的机器人 `@lucascryptomonitorbot` 发送一条消息：`/start`
2. 在浏览器打开这个链接：
   ```
   https://api.telegram.org/bot8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68/getUpdates
   ```
3. 在页面中搜索 `"id":` 找到一个数字，比如：
   ```json
   "chat": {
       "id": 1234567890,    ← 这就是你的 Chat ID
       "first_name": "Lucas",
       ...
   }
   ```

---

## ✅ 第二步：设置数据库密码（1分钟）

### 生成强密码

**在你的本地电脑运行**（Mac/Linux）：
```bash
# 生成 PostgreSQL 密码
echo "PostgreSQL密码: $(openssl rand -base64 16)"

# 生成 Redis 密码
echo "Redis密码: $(openssl rand -base64 16)"
```

**或者自己设置**（建议16位以上，包含大小写字母、数字、特殊字符）：
- PostgreSQL密码示例: `Pg@2024!Crypto#Secure`
- Redis密码示例: `Redis$2024!Secure#Key`

### 记录下来（部署时需要）：
```
PostgreSQL密码: ___________________________
Redis密码: _________________________________
```

---

## ✅ 第三步：连接到腾讯云服务器（1分钟）

### 方法1：使用网页终端（最简单）

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)
2. 找到你的服务器（IP: 119.28.43.237）
3. 点击「登录」按钮
4. 选择「浏览器 VNC 登录」
5. 输入用户名和密码

### 方法2：使用 SSH（推荐）

**Mac/Linux**：
```bash
ssh root@119.28.43.237
# 输入服务器密码
```

**Windows**：
- 使用 PuTTY 或 Windows Terminal
- 主机：119.28.43.237
- 端口：22
- 用户名：root

---

## ✅ 第四步：上传部署脚本（2分钟）

### 方法1：直接在服务器上创建（推荐）

连接到服务器后，执行：

```bash
# 创建脚本文件
cat > deploy_tencent_cloud.sh << 'DEPLOY_SCRIPT_END'
```

然后**复制整个 `deploy_tencent_cloud.sh` 的内容**，粘贴到终端，最后输入：
```bash
DEPLOY_SCRIPT_END

# 给脚本添加执行权限
chmod +x deploy_tencent_cloud.sh
```

### 方法2：从本地上传

**在你的本地电脑运行**：
```bash
cd /Users/szld2403203/Library/Mobile\ Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot

# 上传脚本
scp deploy_tencent_cloud.sh root@119.28.43.237:/root/

# 连接到服务器
ssh root@119.28.43.237
```

---

## ✅ 第五步：运行自动部署脚本（5-10分钟）

在服务器上执行：

```bash
# 确保脚本有执行权限
chmod +x deploy_tencent_cloud.sh

# 运行部署脚本
bash deploy_tencent_cloud.sh
```

### 按照提示输入信息：

脚本会依次询问以下信息，**复制粘贴你准备好的内容**：

1. **是否继续？** → 输入 `y`

2. **PostgreSQL 用户名** → 直接回车（使用默认 cryptobot）

3. **PostgreSQL 密码** → 输入你设置的密码（第二步设置的）

4. **数据库名** → 直接回车（使用默认 crypto_monitor）

5. **Redis 密码** → 输入你设置的密码（第二步设置的）

6. **获取项目代码的方式**：
   - 如果代码已上传到GitHub：选择 `1`，输入仓库地址
   - 如果手动上传：选择 `2`，稍后再上传代码

7. **Telegram Bot Token** → 输入：`8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68`

8. **Telegram Chat ID** → 输入你在第一步获取的数字（如：1234567890）

9. **是否配置 Binance API** → 输入 `n`（公开数据不需要）

10. **是否看到成功消息** → 如果看到 "✅ Bot is running!"，输入 `y`

11. **是否配置防火墙** → 输入 `y`（推荐）

12. **是否配置自动备份** → 输入 `y`（推荐）

---

## ✅ 第六步：验证部署（2分钟）

### 1. 检查服务状态

```bash
# 查看运行状态
supervisorctl status crypto-monitor-bot

# 应该显示: crypto-monitor-bot   RUNNING   pid 1234, uptime 0:01:00
```

### 2. 查看日志

```bash
# 查看实时日志
tail -f /var/log/crypto-monitor-bot.log

# 按 Ctrl+C 停止查看
```

**期望看到的输出**：
```
🚀 Starting Crypto Monitor Bot...
✅ Database connections established
✅ Selected 50 symbols
✅ Subscribed to 50 symbols
✅ Bot is running! Press Ctrl+C to stop.
```

### 3. 测试 Telegram 通知

**方法1：等待自然告警**
- 等待几分钟，当有价格波动时，你会在 Telegram 收到消息

**方法2：发送测试消息**

在服务器上运行：
```bash
cd /opt/crypto-monitor-bot
source venv/bin/activate
python3 << 'PYTHON_TEST'
import os
from dotenv import load_dotenv
load_dotenv()

from src.notifiers.telegram_notifier import TelegramNotifier
import asyncio

async def test():
    notifier = TelegramNotifier()
    await notifier.send_message("🎉 部署成功！机器人已开始监控...")

asyncio.run(test())
PYTHON_TEST
```

你应该会在 Telegram 收到测试消息！

---

## 🎉 部署完成！

### 常用命令

**查看状态**：
```bash
supervisorctl status
```

**查看日志**：
```bash
tail -f /var/log/crypto-monitor-bot.log
```

**重启服务**：
```bash
supervisorctl restart crypto-monitor-bot
```

**停止服务**：
```bash
supervisorctl stop crypto-monitor-bot
```

**启动服务**：
```bash
supervisorctl start crypto-monitor-bot
```

---

## 🔧 如果遇到问题

### 问题1：无法获取 Chat ID

**解决**：
1. 确保给机器人发送了 `/start` 命令
2. 使用 @userinfobot 获取ID
3. 确保ID是纯数字，不是 @username

### 问题2：脚本运行出错

**查看错误信息**：
```bash
tail -n 50 /var/log/crypto-monitor-bot.log
```

**常见错误**：
- 数据库连接失败 → 检查密码是否正确
- Telegram 发送失败 → 检查 Token 和 Chat ID
- 网络连接失败 → 检查服务器网络

### 问题3：上传代码时选择了方式2

**上传代码到服务器**：

在本地电脑运行：
```bash
cd /Users/szld2403203/Library/Mobile\ Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot

# 排除不需要的文件
tar -czf crypto-bot.tar.gz \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='venv' \
  --exclude='.env' \
  .

# 上传到服务器
scp crypto-bot.tar.gz root@119.28.43.237:/opt/crypto-monitor-bot/

# 连接到服务器
ssh root@119.28.43.237

# 解压
cd /opt/crypto-monitor-bot
tar -xzf crypto-bot.tar.gz
rm crypto-bot.tar.gz

# 重新运行部署脚本的后续步骤
```

---

## 📝 部署信息记录

**请保存这些信息**：

```
服务器IP: 119.28.43.237
SSH端口: 22
SSH用户: root

项目目录: /opt/crypto-monitor-bot
日志文件: /var/log/crypto-monitor-bot.log
备份目录: /opt/backups/

PostgreSQL:
  - 主机: localhost:5432
  - 数据库: crypto_monitor
  - 用户名: cryptobot
  - 密码: [你设置的密码]

Redis:
  - 主机: localhost:6379
  - 密码: [你设置的密码]

Telegram:
  - Bot Token: 8612731213:AAEuWYfSt7AiAe10rParFxGZo0SoJFH1T68
  - Chat ID: [你获取的数字]
```

---

## 🎯 下一步

1. **监控运行状态**
   - 定期查看日志：`tail -f /var/log/crypto-monitor-bot.log`
   - 查看系统资源：`htop`

2. **调整配置**（可选）
   - 修改监控币种数量：编辑 `/opt/crypto-monitor-bot/config.yaml`
   - 修改告警阈值：编辑 `/opt/crypto-monitor-bot/config.yaml`
   - 修改后记得重启：`supervisorctl restart crypto-monitor-bot`

3. **启用高级功能**（可选）
   - 查看文档：`/opt/crypto-monitor-bot/docs/`
   - 妖币交易策略：`docs/strategies/pump-dump-trading.md`

---

## 📞 需要帮助？

如果在任何步骤遇到问题，可以：
1. 查看详细日志
2. 查阅 [完整文档](TENCENT_CLOUD_DEPLOYMENT.md)
3. 提交问题到 GitHub Issues

---

**祝你部署顺利！** 🚀
