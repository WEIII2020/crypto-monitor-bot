# 更新日志 (Changelog)

## [v2.0-unified-200] - 2026-04-17

### 🎉 重大更新

#### 监控能力提升 4倍
- ✅ **监控币种**: 从 50 个扩大到 **200 个**
- ✅ **交易量范围**: $1M - $500M（之前 $5M - $50M）
- ✅ **包含主流币**: 现在可以监控更大市值的币种

#### 核心优化
- ✅ **OI监控优化**: 阈值从 50%/5% 提升到 60%/3%（更严格，减少误报）
- ✅ **信号融合优化**: 观察门槛 60→65，买入门槛 80→85（更谨慎）
- ✅ **波动监控优化**: 告警冷却从 5分钟延长到 10分钟（减少误报）
- ✅ **Redis增强**: 新增通用 get/set 方法

#### Lana 交易引擎集成
- ✅ **完整保留** `hermes_integration/` 模块
  - `lana_trading_engine.py` - 交易引擎核心
  - `monitor_data_reader.py` - 数据读取器
  - `telegram_commands.py` - Telegram 命令集成

#### 开发者体验
- ✅ **完整测试套件**: 7 个测试文件覆盖核心功能
- ✅ **环境变量模板**: 新增 `.env.example`
- ✅ **自动化部署**: `deploy_unified_v2.sh` 一键部署脚本
- ✅ **详细文档**: 
  - `CODE_COMPARISON_SUMMARY.md` - 代码对比总结
  - `INTEGRATION_PLAN.md` - 集成计划
  - `CHANGELOG.md` - 更新日志

### 📊 版本对比

| 特性 | 服务器版 (v1.0) | 统一版 (v2.0) |
|------|----------------|---------------|
| 监控币种 | 50 | **200** ⬆️ 4x |
| OI 阈值 | 50%/5% | **60%/3%** 更严格 |
| 信号阈值 | 60/80 | **65/85** 更谨慎 |
| 告警冷却 | 5分钟 | **10分钟** 减少误报 |
| Lana集成 | ❌ | **✅** |
| 测试覆盖 | 基础 | **完整** |
| 部署自动化 | 手动 | **一键部署** |

### 🔧 配置变更

#### config.yaml
```yaml
# 之前
symbols:
  max_count: 50
  min_volume_usd: 5000000
  max_volume_usd: 50000000

# 现在
symbols:
  max_count: 200                # +150 币种
  min_volume_usd: 1000000       # 降低门槛
  max_volume_usd: 500000000     # 扩大范围
```

#### main.py
```python
# 之前
self.symbols = await self.symbol_selector.get_monitoring_list(max_symbols=50)

# 现在
self.symbols = await self.symbol_selector.get_monitoring_list(max_symbols=200)
```

### 📁 新增文件

```
crypto-monitor-bot-v2.0/
├── .env.example                      # ✨ 新增
├── CODE_COMPARISON_SUMMARY.md        # ✨ 新增
├── INTEGRATION_PLAN.md               # ✨ 新增
├── CHANGELOG.md                      # ✨ 新增
├── deploy_unified_v2.sh             # ✨ 新增
└── hermes_integration/              # ✨ 完整保留
    ├── lana_trading_engine.py
    ├── monitor_data_reader.py
    └── telegram_commands.py
```

### 🚀 升级指南

#### 从 v1.0 (50币种) 升级到 v2.0 (200币种)

**方法 1: 使用自动化脚本（推荐）**
```bash
# 1. 在本地执行
./deploy_unified_v2.sh

# 脚本会自动:
# - 打包代码
# - 备份服务器旧版本
# - 上传并部署新版本
# - 验证部署结果
```

**方法 2: 手动部署**
```bash
# 1. 打包本地代码
tar -czf crypto-bot-v2.0.tar.gz \
  --exclude=venv \
  --exclude=__pycache__ \
  --exclude=.git \
  --exclude=hermes_server_code \
  .

# 2. 上传到服务器
scp crypto-bot-v2.0.tar.gz root@119.28.43.237:/root/

# 3. SSH登录服务器
ssh root@119.28.43.237

# 4. 备份旧版本
cd /root
tar -czf backups/crypto-bot-v1.0-backup.tar.gz crypto-monitor-bot

# 5. 部署新版本
rm -rf crypto-monitor-bot
mkdir crypto-monitor-bot
tar -xzf crypto-bot-v2.0.tar.gz -C crypto-monitor-bot/

# 6. 安装依赖
cd crypto-monitor-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 7. 配置环境变量
cp .env.example .env
vim .env  # 填入你的配置

# 8. 启动服务
./start.sh
```

### ⚠️ 重要提示

#### 性能考虑
- **200 币种** 比 50 币种消耗更多资源
- 建议服务器配置: 
  - CPU: 2核+
  - RAM: 4GB+
  - 网络: 稳定连接

#### 循序渐进部署
如果担心性能，可以先测试中等规模:
```yaml
# config.yaml
symbols:
  max_count: 100  # 先测试100个币种
```

待稳定后再扩展到 200。

#### 数据库性能
- PostgreSQL: 确保有足够磁盘空间（200币种产生更多数据）
- Redis: 建议至少 512MB 内存

### 🐛 已知问题

暂无

### 📝 下一版本计划 (v2.1)

- [ ] 增加 WebSocket 断线重连优化
- [ ] Telegram Bot 交互式配置界面
- [ ] 实时性能监控仪表盘
- [ ] 币种热度自动调整（动态选择最活跃的200个）
- [ ] 支持多个 Telegram 群组通知

### 🤝 贡献者

- 代码整合与优化: Claude (Anthropic)
- 原始开发: WEIII2020

---

## [v1.0-lana-optimized] - 2026-04-15

### 初始发布
- ✅ 监控 50 个币种
- ✅ 9 个分析器
- ✅ PostgreSQL + Redis 存储
- ✅ Telegram 实时通知
- ✅ 性能监控系统

---

*更多历史版本请参考 Git 提交记录*
