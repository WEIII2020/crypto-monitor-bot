# 📚 文档索引与重组方案

## 🎯 当前问题

项目根目录有**15个Markdown文档**，结构混乱：
- ❌ 文档重复（多个"快速开始"）
- ❌ 命名不清晰
- ❌ 没有统一入口
- ❌ 新旧文档混杂

---

## ✅ 重组方案

### 核心原则

1. **一个入口**: `README.md` 作为唯一起点
2. **结构清晰**: 按用途分类，不超过3层
3. **避免重复**: 合并相似内容
4. **归档过时**: 旧文档移至 `docs/archive/`

---

## 📁 新文档结构

```
crypto-monitor-bot/
├── README.md                    # ⭐ 主入口（简洁版）
├── GETTING_STARTED.md           # 🚀 5分钟快速开始
├── CHANGELOG.md                 # 📝 更新日志
│
├── docs/                        # 📚 主文档目录
│   ├── user-guide/              # 👤 用户指南
│   │   ├── features.md          # 功能介绍
│   │   ├── configuration.md     # 配置指南
│   │   ├── alerts.md            # 告警说明
│   │   └── faq.md               # 常见问题
│   │
│   ├── strategies/              # 🎯 策略文档
│   │   ├── passive-monitoring.md    # 被动监控
│   │   ├── pump-dump-trading.md     # 妖币策略
│   │   └── rave-analysis.md         # RAVE控盘分析
│   │
│   ├── technical/               # 🔧 技术文档
│   │   ├── architecture.md      # 系统架构
│   │   ├── development.md       # 开发指南
│   │   ├── performance.md       # 性能优化
│   │   └── troubleshooting.md   # 故障排查
│   │
│   └── archive/                 # 📦 归档文档
│       ├── old-quickstart.md
│       ├── system-diagnosis.md
│       └── ...
│
└── config.yaml                  # ⚙️ 配置文件
```

---

## 📋 文档映射表

### 保留并重构的文档

| 当前文件 | 新位置/处理 | 原因 |
|---------|-----------|------|
| `README.md` | ✏️ 重写为简洁入口 | 作为主入口 |
| `RAVE_ANALYSIS_AND_OPTIMIZATION.md` | → `docs/strategies/rave-analysis.md` | 保留，重命名 |
| `PUMP_DUMP_STRATEGY.md` | → `docs/strategies/pump-dump-trading.md` | 保留，重命名 |
| `config.yaml` | ✅ 保留 | 配置文件 |

### 合并的文档

| 当前文件 | 合并到 | 原因 |
|---------|-------|------|
| `QUICKSTART.md` | `GETTING_STARTED.md` | 内容重复 |
| `START_HERE.md` | `GETTING_STARTED.md` | 内容重复 |
| `PUMP_DUMP_QUICK_START.md` | `docs/strategies/pump-dump-trading.md` | 合并到策略文档 |
| `UPGRADE_SUCCESS.md` | `CHANGELOG.md` | 转为更新日志 |
| `IMPLEMENTATION_GUIDE.md` | `docs/technical/development.md` | 合并到开发指南 |

### 归档的文档（移至 docs/archive/）

| 当前文件 | 原因 |
|---------|------|
| `WHALE_DETECTOR_DESIGN.md` | 已过时（已被V2替代） |
| `SYSTEM_DIAGNOSIS.md` | 一次性诊断文档 |
| `OPTIMIZATION_GUIDE.md` | 已完成，内容过时 |
| `OPTIMIZATION_COMPLETE.md` | 已完成的报告 |
| `FINAL_REPORT.md` | 已完成的报告 |
| `UPGRADE_SUMMARY.md` | 已整合到CHANGELOG |
| `PUMP_DUMP_UPGRADE_COMPLETE.md` | 已整合到CHANGELOG |

---

## 🚀 新文档内容规划

### 1. README.md（主入口）

**目标:** 5分钟了解项目  
**内容:**
- 一句话介绍
- 核心功能（表格）
- 快速开始（3步）
- 文档导航
- 贡献与支持

**字数:** ~800字

### 2. GETTING_STARTED.md（快速开始）

**目标:** 10分钟完成安装配置  
**内容:**
- 环境要求
- 安装步骤
- 基础配置
- 启动验证
- 下一步

**字数:** ~1200字

### 3. CHANGELOG.md（更新日志）

**目标:** 追踪所有版本变化  
**内容:**
- v2.0.0 - 妖币策略（2026-04-14）
- v1.5.0 - WhaleDetectorV2（2026-04-14）
- v1.0.0 - 基础版本

**格式:** 标准changelog格式

### 4. docs/user-guide/features.md（功能介绍）

**目标:** 15分钟了解所有功能  
**内容:**
- 被动监控功能
- 主动交易功能
- 告警类型
- 使用场景

**字数:** ~2000字

### 5. docs/strategies/pump-dump-trading.md（妖币策略）

**目标:** 完整理解妖币策略  
**内容:**
- 策略原理
- 8条铁律
- 使用步骤
- 风险控制
- 实战案例

**字数:** ~3000字
**来源:** 合并 `PUMP_DUMP_STRATEGY.md` + `PUMP_DUMP_QUICK_START.md`

### 6. docs/strategies/rave-analysis.md（RAVE分析）

**目标:** 深度理解控盘检测  
**内容:**
- RAVE案例拆解
- 检测指标
- 实施方案
- 优化路线图

**字数:** ~4000字
**来源:** 保留 `RAVE_ANALYSIS_AND_OPTIMIZATION.md` 内容

---

## 🔄 实施步骤

### Phase 1: 创建新结构（10分钟）

```bash
# 1. 创建目录
mkdir -p docs/{user-guide,strategies,technical,archive}

# 2. 移动要归档的文档
mv WHALE_DETECTOR_DESIGN.md docs/archive/
mv SYSTEM_DIAGNOSIS.md docs/archive/
mv OPTIMIZATION_GUIDE.md docs/archive/
mv OPTIMIZATION_COMPLETE.md docs/archive/
mv FINAL_REPORT.md docs/archive/
mv UPGRADE_SUMMARY.md docs/archive/
mv PUMP_DUMP_UPGRADE_COMPLETE.md docs/archive/
```

### Phase 2: 重写核心文档（30分钟）

```bash
# 重写
1. README.md（主入口）
2. GETTING_STARTED.md（快速开始）
3. CHANGELOG.md（更新日志）
```

### Phase 3: 整合策略文档（20分钟）

```bash
# 合并妖币相关文档
cat PUMP_DUMP_STRATEGY.md PUMP_DUMP_QUICK_START.md \
    > docs/strategies/pump-dump-trading.md

# 移动RAVE文档
mv RAVE_ANALYSIS_AND_OPTIMIZATION.md docs/strategies/rave-analysis.md

# 删除原文件
rm PUMP_DUMP_STRATEGY.md PUMP_DUMP_QUICK_START.md
```

### Phase 4: 创建用户指南（20分钟）

```bash
# 创建新文档
1. docs/user-guide/features.md
2. docs/user-guide/configuration.md
3. docs/user-guide/alerts.md
4. docs/user-guide/faq.md
```

### Phase 5: 清理（5分钟）

```bash
# 删除重复文档
rm QUICKSTART.md START_HERE.md UPGRADE_SUCCESS.md
rm IMPLEMENTATION_GUIDE.md

# 验证
tree docs/
```

---

## 📊 重组前后对比

### 重组前（混乱）

```
根目录: 15个.md文件
  ├─ 多个"快速开始"（3个）
  ├─ 多个"升级完成"（3个）
  ├─ 过时文档（6个）
  └─ 命名不统一
```

### 重组后（清晰）

```
根目录: 3个核心文档
  ├─ README.md（入口）
  ├─ GETTING_STARTED.md（快速开始）
  └─ CHANGELOG.md（更新日志）

docs/:
  ├─ user-guide/（用户指南，4个文档）
  ├─ strategies/（策略文档，3个文档）
  ├─ technical/（技术文档，4个文档）
  └─ archive/（归档，7个文档）
```

---

## ✅ 实施检查清单

**准备阶段:**
- [ ] 备份当前所有文档
- [ ] 创建文档目录结构

**执行阶段:**
- [ ] 移动归档文档
- [ ] 重写 README.md
- [ ] 创建 GETTING_STARTED.md
- [ ] 创建 CHANGELOG.md
- [ ] 合并妖币策略文档
- [ ] 整理RAVE分析文档
- [ ] 创建用户指南文档
- [ ] 创建技术文档

**验证阶段:**
- [ ] 检查所有链接
- [ ] 验证文档完整性
- [ ] 测试快速开始流程
- [ ] 清理临时文件

**完成阶段:**
- [ ] 更新 README.md 中的文档链接
- [ ] 删除重复/过时文档
- [ ] 提交变更

---

## 🎯 预期效果

### 用户体验

**重组前:**
- ❌ 不知道从哪个文档开始
- ❌ 看了5个文档还不知道如何启动
- ❌ 文档内容重复浪费时间

**重组后:**
- ✅ README.md 一目了然
- ✅ GETTING_STARTED.md 10分钟上手
- ✅ 按需深入，不重复

### 维护性

**重组前:**
- ❌ 更新需要修改多个文档
- ❌ 容易漏掉同步
- ❌ 难以找到对应文档

**重组后:**
- ✅ 单一来源原则
- ✅ 清晰的文档职责
- ✅ 易于维护更新

---

## 📝 命名规范

### 文件命名

- 使用小写 + 连字符: `pump-dump-trading.md`
- 简洁明了: `faq.md` 而不是 `frequently-asked-questions.md`
- 避免缩写: `configuration.md` 而不是 `config.md`

### 标题命名

- 清晰描述内容: "妖币策略完整指南"
- 避免模糊: 不要用"文档1"、"说明"
- 统一格式: Emoji + 中文标题

---

## 🎊 总结

这个重组方案将：

1. ✅ **减少文档数量**: 15个 → 约12个（含归档）
2. ✅ **提升可读性**: 清晰的层次结构
3. ✅ **避免重复**: 合并相似内容
4. ✅ **易于维护**: 单一来源原则
5. ✅ **新手友好**: 5分钟找到需要的内容

**下一步:** 开始执行 Phase 1？

---

**创建日期:** 2026-04-14  
**预计完成时间:** 1-2小时  
**维护者:** 项目团队
