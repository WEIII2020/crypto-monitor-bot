# 🔄 代码同步策略

## 📊 当前状态分析

### GitHub 状态（本地 + 远程）
```
✅ 最新提交: 22b798a - Phase 1 毫秒级监控
✅ 分支: main
✅ 文件完整性: 100%
```

### 腾讯云服务器状态
```
⚠️ 不是 Git 仓库 (fatal: not a git repository)
✅ 运行中: v2.0-unified-200 (200币种监控)
❓ 代码版本: 未知（手动上传的 tar.gz）
```

---

## 🎯 同步策略

### 核心原则

```
┌─────────────────────────────────────────────────────────┐
│                    代码管理策略                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📦 基础监控（v2.0-unified-200）                        │
│     ↓                                                   │
│  以腾讯云服务器为准 ← 生产环境，稳定运行                 │
│     ↓                                                   │
│  保存到 GitHub: production 分支                         │
│                                                         │
│  ───────────────────────────────────────────────        │
│                                                         │
│  🚀 Phase 1/2/3 优化（新功能）                          │
│     ↓                                                   │
│  以 GitHub main 分支为准 ← 开发环境                     │
│     ↓                                                   │
│  测试通过后 → 合并到 production                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔧 实施步骤

### Step 1: 从服务器下载生产代码

在**本地终端**执行：

```bash
# 1. 创建下载脚本
cat > /tmp/download_production.sh << 'EOF'
#!/bin/bash
SERVER="119.28.43.237"
SERVER_DIR="/root/crypto-monitor-bot"
LOCAL_DIR="/tmp/production-code"

echo "📦 下载生产环境代码..."

# 创建本地目录
mkdir -p $LOCAL_DIR

# 下载核心文件（排除大文件和日志）
ssh root@$SERVER "cd $SERVER_DIR && tar --exclude='venv' --exclude='__pycache__' --exclude='*.log' --exclude='*.pid' -czf /tmp/production.tar.gz ."

# 复制到本地
scp root@$SERVER:/tmp/production.tar.gz $LOCAL_DIR/

# 解压
cd $LOCAL_DIR
tar -xzf production.tar.gz

echo "✅ 下载完成: $LOCAL_DIR"
ls -lh $LOCAL_DIR
EOF

chmod +x /tmp/download_production.sh
/tmp/download_production.sh
```

### Step 2: 创建 production 分支

```bash
cd /Users/szld2403203/Library/Mobile\ Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot

# 创建并切换到 production 分支
git checkout -b production

# 复制生产环境代码（覆盖）
cp -r /tmp/production-code/* .

# 移除 Phase 1 文件（保持生产环境纯净）
git rm -f main_realtime.py quick_deploy_phase1.sh 2>/dev/null || true
git rm -f src/collectors/binance_realtime_collector.py 2>/dev/null || true
git rm -f src/utils/sliding_window.py 2>/dev/null || true
git rm -f tests/test_realtime_system.py 2>/dev/null || true

# 提交生产版本
git add -A
git commit -m "production: 腾讯云生产环境代码快照

- 版本: v2.0-unified-200
- 监控: 200币种
- 状态: 稳定运行
- 来源: 腾讯云服务器 (119.28.43.237)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

# 推送到 GitHub
git push origin production

# 切回 main 分支
git checkout main
```

### Step 3: 在服务器上初始化 Git

在**服务器终端**执行：

```bash
cd /root/crypto-monitor-bot

# 初始化 Git（不影响运行）
git init
git remote add origin https://github.com/WEIII2020/crypto-monitor-bot.git

# 拉取 production 分支
git fetch origin production
git checkout -b production origin/production

# 验证
git status
git log --oneline -5
```

---

## 📋 分支管理规范

### 分支结构

```
crypto-monitor-bot (GitHub)
│
├── main (开发分支) ← Phase 1/2/3 优化
│   ├── 包含: 毫秒级监控、预判交易、自动执行
│   ├── 状态: 开发中
│   └── 部署: 测试环境
│
└── production (生产分支) ← 稳定的监控系统
    ├── 包含: v2.0-unified-200 (200币种)
    ├── 状态: 稳定运行
    └── 部署: 腾讯云服务器
```

### 工作流程

```
┌─────────────────────────────────────────────┐
│         日常开发流程                         │
├─────────────────────────────────────────────┤
│                                             │
│  1️⃣ 开发新功能（本地）                      │
│     ↓                                       │
│     git checkout main                       │
│     编写 Phase 1/2/3 代码                   │
│     git commit + push                       │
│                                             │
│  2️⃣ 测试验证                                │
│     ↓                                       │
│     本地测试 main 分支                       │
│     或部署到测试服务器                       │
│                                             │
│  3️⃣ 合并到生产（慎重！）                     │
│     ↓                                       │
│     git checkout production                 │
│     git merge main                          │
│     git push origin production              │
│                                             │
│  4️⃣ 服务器更新                              │
│     ↓                                       │
│     SSH 到腾讯云                             │
│     cd /root/crypto-monitor-bot            │
│     git pull origin production             │
│     重启服务                                 │
│                                             │
└─────────────────────────────────────────────┘
```

---

## 🚀 立即执行的方案

由于你的需求是：
- ✅ **生产监控以腾讯云为准** → 保持当前运行
- ✅ **Phase 1/2/3 以 GitHub 为准** → 独立开发

### 推荐方案：双轨制

**方案 A: 不影响生产环境（推荐）**

```bash
# 在腾讯云服务器上

# 1. 保持当前监控继续运行
ps aux | grep "python.*main.py"  # 验证运行中

# 2. 创建新目录测试 Phase 1
cd /root
git clone https://github.com/WEIII2020/crypto-monitor-bot.git crypto-monitor-phase1

# 3. 进入新目录
cd crypto-monitor-phase1

# 4. 安装依赖
python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt
pip install numpy

# 5. 复制 .env 文件
cp /root/crypto-monitor-bot/.env .

# 6. 测试 Phase 1（不影响生产）
python main_realtime.py  # 测试模式（5个币种）
```

**结果**：
- `/root/crypto-monitor-bot/` ← 生产环境（200币种，继续运行）
- `/root/crypto-monitor-phase1/` ← 测试环境（Phase 1，独立测试）

---

## 📊 同步检查清单

### 检查腾讯云代码

在**服务器**执行：

```bash
cd /root/crypto-monitor-bot

# 检查主要文件
echo "=== 核心文件 ==="
ls -lh main.py config.yaml .env

echo "=== 分析器 ==="
ls -lh src/analyzers/*.py

echo "=== 运行状态 ==="
ps aux | grep "python.*main.py"

echo "=== 配置版本 ==="
grep "max_count" config.yaml
grep "max_symbols" main.py
```

### 检查 GitHub 代码

在**本地**执行：

```bash
cd /Users/szld2403203/Library/Mobile\ Documents/com~apple~CloudDocs/Cursor/crypto-monitor-bot

# 查看当前分支
git branch

# 查看提交历史
git log --oneline --graph --all -10

# 查看文件差异
git diff main production  # 如果 production 分支存在
```

---

## 💡 我的建议

基于你的需求，我建议采用**方案 A（双轨制）**：

### 立即执行

1. **保持生产环境不动**
   - `/root/crypto-monitor-bot/` 继续运行
   - 不改动任何文件

2. **创建独立测试环境**
   - 克隆 GitHub 到新目录
   - 测试 Phase 1 功能
   - 验证通过后再决定是否替换

3. **好处**
   - ✅ 零风险（生产不受影响）
   - ✅ 可以对比新旧版本
   - ✅ 随时可以切换

---

## ❓ 你希望怎么做？

请告诉我：

**选项 1**: 执行双轨制（推荐）
- 保持生产不变
- 独立测试 Phase 1

**选项 2**: 直接升级生产
- 备份当前环境
- 直接部署 Phase 1

**选项 3**: 先同步到 GitHub
- 下载腾讯云代码
- 创建 production 分支
- 再考虑 Phase 1

我会根据你的选择提供详细步骤！🎯
