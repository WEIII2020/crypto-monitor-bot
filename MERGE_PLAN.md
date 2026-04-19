# 🔄 项目合并方案

## 📊 现状分析

### 项目 1: crypto-monitor-bot
**核心功能：**
- ✅ 实时数据采集（BinanceRealtimeCollector）
- ✅ 交易信号生成（V4A/V7/V8/LONG 策略）
- ✅ 妖币检测（ManipulationDetectorV2）
- ✅ Lana 交易引擎
- ✅ Telegram 通知
- ✅ 多运行模式（monitor/signal/trade）
- ✅ 配置文件系统
- ✅ 一键部署脚本

**架构：**
```
crypto-monitor-bot/
├── main_phase2.py          # 主程序
├── src/
│   ├── collectors/         # 数据采集
│   ├── analyzers/          # 信号分析
│   ├── trading/            # 交易执行
│   └── notifiers/          # 通知系统
└── config/                 # 配置文件
```

### 项目 2: Hermes Agent
**核心功能：**
- ✅ Hermes Agent 框架（完整的 Agent 系统）
- ✅ 插件系统（tools/）
- ✅ crypto_monitor 工具（已有基础集成）
- ✅ Telegram Bot 交互
- ✅ 命令系统
- ✅ 数据读取器

**架构：**
```
hermes-agent/
├── run_agent.py            # Agent 入口
├── agent/                  # Agent 核心
├── tools/
│   └── crypto_monitor/     # 加密货币监控工具
│       ├── commands.py
│       ├── data_reader.py
│       └── runner.py
└── hermes_cli/            # CLI 工具
```

---

## 🎯 合并目标

将两个项目合并为一个统一的系统：

**统一后的架构：**
```
crypto-monitor-bot/          # 主项目（保留现有）
├── main_phase2.py          # 核心监控 Bot
├── hermes_agent.py         # Hermes Agent 入口（新增）
│
├── src/
│   ├── collectors/         # 数据采集（保留）
│   ├── analyzers/          # 信号分析（保留）
│   ├── trading/            # 交易执行（保留）
│   ├── notifiers/          # 通知系统（保留）
│   │
│   ├── hermes/             # Hermes Agent 模块（新增）
│   │   ├── agent_core/     # Agent 核心逻辑
│   │   ├── commands/       # 命令系统
│   │   ├── plugins/        # 插件系统
│   │   └── telegram_bot/   # Telegram 交互
│   │
│   └── integration/        # 集成层（新增）
│       ├── data_bridge.py  # 数据桥接
│       └── signal_handler.py # 信号处理
│
├── config/
│   ├── config.yaml         # 监控 Bot 配置
│   └── hermes_config.yaml  # Hermes Agent 配置
│
└── tools/                  # Hermes 工具集（从 hermes-agent 迁移）
    └── crypto_monitor/     # 加密货币监控工具
```

---

## ✨ 合并优势

### 1. 统一的数据层
- crypto-monitor-bot 负责数据采集和信号生成
- Hermes Agent 通过 `data_bridge.py` 读取数据
- 避免重复采集，节省资源

### 2. 增强的交互能力
- Hermes Agent 提供 Telegram Bot 交互
- 用户可以通过命令查询实时数据
- 支持手动触发交易、查看历史信号等

### 3. 模块化设计
- 两个系统可以独立运行
- 也可以协同工作
- 便于维护和扩展

### 4. 功能互补
| 功能 | crypto-monitor-bot | Hermes Agent | 合并后 |
|------|-------------------|--------------|--------|
| 数据采集 | ✅ 完善 | ❌ 基础 | ✅ 使用 crypto-monitor-bot |
| 信号生成 | ✅ 完善 | ❌ 无 | ✅ 使用 crypto-monitor-bot |
| Telegram 交互 | ✅ 单向推送 | ✅ 双向交互 | ✅ 使用 Hermes Agent |
| 命令系统 | ❌ 无 | ✅ 完善 | ✅ 使用 Hermes Agent |
| 交易执行 | ✅ Lana 引擎 | ❌ 无 | ✅ Hermes 可调用 Lana |

---

## 🚀 合并步骤

### Phase 1: 准备工作（已完成）
- ✅ crypto-monitor-bot 已优化合并
- ✅ 修复所有关键 Bug
- ✅ 统一配置系统
- ✅ 完善文档

### Phase 2: 迁移 Hermes Agent 核心（10分钟）
1. 将 `hermes-agent/agent/` → `src/hermes/agent_core/`
2. 将 `hermes-agent/tools/crypto_monitor/` → `src/hermes/plugins/crypto_monitor/`
3. 提取 Telegram Bot 逻辑 → `src/hermes/telegram_bot/`

### Phase 3: 创建集成层（15分钟）
1. 创建 `src/integration/data_bridge.py`
   - 提供统一的数据访问接口
   - Hermes Agent 通过此接口读取 crypto-monitor-bot 的数据

2. 创建 `src/integration/signal_handler.py`
   - 处理信号分发
   - 同时发送给 Telegram 通知和 Hermes Agent

### Phase 4: 配置整合（5分钟）
1. 创建 `config/hermes_config.yaml`
2. 更新环境变量支持
3. 统一日志系统

### Phase 5: 创建启动脚本（5分钟）
1. `run_unified.sh` - 同时启动两个系统
2. `run_monitor_only.sh` - 只启动监控
3. `run_hermes_only.sh` - 只启动 Hermes Agent

---

## 🎯 合并后的使用场景

### 场景 1: 仅监控模式
```bash
./run.sh monitor
# 只运行 crypto-monitor-bot 数据采集
```

### 场景 2: 信号模式（当前默认）
```bash
./run.sh signal
# crypto-monitor-bot 采集数据 + 生成信号 + Telegram 推送
```

### 场景 3: 交互模式（新增）
```bash
./run_unified.sh
# crypto-monitor-bot + Hermes Agent
# - 自动推送信号
# - Telegram Bot 可交互查询
# - 支持命令操作
```

### 场景 4: 交易模式
```bash
./run_unified.sh trade
# 全功能模式
# - 数据采集 + 信号生成
# - Hermes Agent 交互
# - Lana 自动交易
```

---

## 📝 Hermes Agent 可用命令（合并后）

### 数据查询
```
/status          - 查看系统状态
/signals         - 查看最近信号
/signals BTC     - 查看 BTC 的信号历史
/price BTC       - 查看实时价格
/oi BTC          - 查看持仓量变化
```

### 策略控制
```
/strategies      - 查看策略状态
/enable v4a      - 启用 V4A 策略
/disable v7      - 禁用 V7 策略
/cooldown v8     - 查看 V8 冷却期
```

### 交易控制
```
/positions       - 查看当前持仓
/close BTC       - 平仓 BTC
/trade on/off    - 开启/关闭自动交易
```

### 系统管理
```
/config          - 查看配置
/logs            - 查看最近日志
/restart         - 重启系统
/stats           - 查看统计信息
```

---

## ⚠️ 注意事项

### 1. 资源占用
- **合并前**：两个独立进程，内存 ~800MB
- **合并后**：统一进程，内存 ~600MB
- **优势**：节省 25% 内存

### 2. 配置兼容性
- 保持 `config/config.yaml` 不变
- 新增 `config/hermes_config.yaml`
- 环境变量向后兼容

### 3. 向后兼容
- 现有的 `main_phase2.py` 可以独立运行
- 旧的启动脚本继续有效
- 不影响已部署的系统

---

## 📊 实施优先级

### 🔥 高优先级（立即执行）
1. ✅ 创建 `src/integration/data_bridge.py`
2. ✅ 迁移 Hermes Agent 核心
3. ✅ 创建统一启动脚本

### 🟡 中优先级（本周）
4. 🔄 实现 Telegram Bot 命令
5. 🔄 整合配置系统
6. 🔄 统一日志系统

### 🟢 低优先级（下周）
7. 📝 完善文档
8. 🧪 添加集成测试
9. 🎨 优化用户界面

---

## 🎉 预期效果

合并后的系统将拥有：

✅ **完整的数据采集** - crypto-monitor-bot 的实时监控  
✅ **智能信号生成** - V4A/V7/V8/LONG 策略  
✅ **双向交互** - Hermes Agent 的 Telegram Bot  
✅ **灵活控制** - 通过命令管理系统  
✅ **自动交易** - Lana 引擎  
✅ **统一配置** - 一个配置文件管理所有  
✅ **模块化架构** - 可独立运行或协同工作  

---

## 🚀 立即开始合并

```bash
# 开始执行合并
./merge_projects.sh
```

详细步骤请查看下方的实施指南。
