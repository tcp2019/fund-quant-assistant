# 基金量化助手（Fund Quant Assistant）设计规格

> **Status:** active
> **Created:** 2026-06-21
> **Supersedes:** (none)
> **Superseded by:** (none)

## 目标

构建一个 **Web 端个人基金量化助手**：用户通过上传持仓截图（类似养基宝）导入基金持仓，系统基于公开数据计算量化指标，并通过 **可解释、可复现的规则引擎** 输出买入/卖出/观察建议。v1 面向个人自用（无登录），架构预留多用户与多设备同步能力。

## 背景与定位

- **参考产品**：养基宝（OCR 识图导入、多平台聚合）、[ifund](https://github.com/OrangesHuang/ifund)（簇级仓位与再平衡）、[licai](https://github.com/SnowWarri0r/licai)（配置模板与集中度警告）
- **差异化**：养基宝侧重展示与统计，**不提供买卖建议**；本产品以 **量化信号引擎** 为核心价值
- **合规定位**：个人持仓管理 + 量化分析工具，**非**持牌投资顾问；所有输出附带免责声明，不构成投资建议
- **不做**：盘中实时估值诱导交易、自动下单、付费荐基

## 范围

### 包含（v1）

1. **截图 OCR 导入**：支持支付宝、天天基金、腾讯理财通持仓截图；人工确认后写入持仓
2. **持仓概览 Dashboard**：总市值、盈亏、权重、大类结构、集中度、相关性、组合风险指标
3. **基金数据同步**：通过 akshare / 东方财富公开接口拉取净值、基准、季报持仓、同类排名
4. **三层量化信号引擎**：配置再平衡 + 风险集中度 + 业绩质量 → 综合评分与操作建议
5. **策略参数配置**：目标配置模板（保守/平衡/激进/自定义）、规则阈值可调
6. **快照历史**：每次 OCR 确认或手动编辑产生快照，支持对比
7. **单用户本地部署**：SQLite 存储，无账号系统

### 不包含（v1）

- 用户注册/登录与多设备同步（v2）
- 策略回测与因子选股（Future）
- LLM 自然语言解释层（Future，可选辅助）
- 候选基金自动推荐列表（v1.1；v1 仅提示「增配某大类 ¥X」）
- 自动交易、券商对接
- 盘中实时估值（合规与数据可靠性考虑，仅用 T+1 官方净值）

### 演进路径

| 阶段 | 能力 |
|------|------|
| v1 | 个人自用 + OCR + 信号引擎 |
| v1.1 | 候选基金推荐、浏览器通知 |
| v2 | 账号体系、多设备同步、PostgreSQL |
| Future | 回测、LLM 解释、更多 OCR 来源 |

## 架构

### 技术栈

| 层 | 选型 | 理由 |
|----|------|------|
| 前端 | React + Tailwind + Recharts | 仪表盘与图表生态成熟 |
| 后端 | Python FastAPI | 与 akshare 生态一致，API 开发快 |
| 数据库 | SQLite（v1）→ PostgreSQL（v2） | 零运维，后续加 `users` 表即可演进 |
| OCR | PaddleOCR（本地优先）+ 可选 Vision API | 本地隐私好；Vision 作准确率兜底 |
| 数据 | akshare | 免费公开基金净值与 metadata |

### 组件图

```
┌─────────────────────────────────────────────────────────┐
│  Web Frontend                                           │
│  /import  /holdings  /  /signals  /analysis  /settings  │
└──────────────────────────┬──────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────┐
│  FastAPI Backend                                        │
│  ┌──────────┐ ┌───────────┐ ┌────────────┐ ┌──────────┐ │
│  │ OCR Svc  │ │ Portfolio │ │ Data Sync  │ │ Metrics  │ │
│  └────┬─────┘ └─────┬─────┘ └─────┬──────┘ └────┬─────┘ │
│       │             │             │              │      │
│       └─────────────┴─────────────┴──────────────┘      │
│                           │                             │
│                    ┌──────▼──────┐                      │
│                    │ Signal Engine│                      │
│                    └──────┬──────┘                      │
│                           │                             │
│                    ┌──────▼──────┐                      │
│                    │ SQLite DB   │                      │
│                    └─────────────┘                      │
└─────────────────────────────────────────────────────────┘
         │                              │
    PaddleOCR / Vision              akshare
```

### 数据流

1. **导入流**：上传截图 → OCR 解析 → 结构化 JSON → 用户确认页 → 写入 `holdings` + `portfolio_snapshots`
2. **同步流**：定时/手动触发 → 按持仓基金代码拉净值/基准/季报 → 写入 `fund_nav_history` 等
3. **计算流**：持仓 + 最新净值 → 权重/盈亏/大类分类 → 指标引擎（波动率、夏普、回撤、相关性）→ 信号引擎 → `signals`
4. **建议流**：信号按综合分排序 → 前端展示；含类型、强度、理由、建议金额

### 核心数据模型（v1）

```
portfolio_snapshots(id, created_at, source, note)
holdings(id, snapshot_id, fund_code, fund_name, shares, cost_price,
         market_value, profit, profit_rate, platform, merged_from[])
fund_metadata(code, name, type, category, benchmark_code, manager, ...)
fund_nav_history(code, date, nav, acc_nav)
fund_metrics_cache(code, date, sharpe_1y, max_drawdown_1y, excess_return_1y, ...)
portfolio_metrics(snapshot_id, date, total_value, volatility, sharpe, max_dd, ...)
correlation_matrix(snapshot_id, date, matrix_json)
signals(id, snapshot_id, fund_code, signal_type, score, strength,
        reasons_json, suggested_amount, created_at)
strategy_config(id, template_name, target_weights_json, thresholds_json)
ocr_jobs(id, status, image_paths, parsed_json, confirmed_at)
```

### API 概要

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ocr/upload` | 上传截图，返回解析草稿 |
| POST | `/api/ocr/{job_id}/confirm` | 确认 OCR 结果，创建快照 |
| GET | `/api/portfolio/overview` | 当前概览 |
| GET | `/api/portfolio/holdings` | 持仓明细 |
| GET | `/api/signals` | 信号列表（按 score 排序） |
| GET | `/api/analysis/correlation` | 相关性矩阵 |
| GET | `/api/analysis/risk` | 组合风险指标 |
| POST | `/api/data/sync` | 手动触发数据同步 |
| GET/PUT | `/api/settings/strategy` | 策略模板与阈值 |

### 页面结构

| 路由 | 功能 |
|------|------|
| `/` | 总览 Dashboard |
| `/import` | 截图上传 + OCR 确认 |
| `/holdings` | 持仓明细 + 手动编辑 |
| `/signals` | 买卖信号（优先级排序） |
| `/analysis` | 相关性、行业暴露、风险指标 |
| `/settings` | 目标配置、规则阈值、数据同步 |

## 功能详述

### 1. 截图 OCR 导入

**支持来源（v1）**：支付宝、天天基金、腾讯理财通。

**识别字段**：基金名称/代码、持有份额、成本价、当前市值、持有收益、收益率。

**流程**：
1. 用户上传 1–N 张截图
2. OCR + 布局模板匹配（按 App 分 parser）
3. 展示可编辑确认页（量化系统要求数据准确，OCR 不可静默入库）
4. 确认后创建快照；同一基金多平台持有按代码合并，保留 `platform` 标签

**校验**：识别出的市值 ≈ 份额 × 净值（误差 > 2% 标黄警告）。

### 2. 持仓概览

| 模块 | 内容 |
|------|------|
| 总览 | 总市值、总成本、总盈亏、最新净值日涨跌 |
| 持仓表 | 权重%、成本、现价、浮盈、持有天数 |
| 结构 | 大类饼图：股票/债券/货币/QDII/黄金/其他 |
| 集中度 | Top5 单只占比、行业暴露（季报持仓推算） |
| 相关性 | 90 日收益相关系数矩阵 |
| 风险 | 组合 1 年波动率、最大回撤、夏普比率 |

### 3. 量化信号引擎

采用 **三层信号 + 综合评分**，每层可开关、阈值可调。

#### 层 1：配置再平衡（权重 40%）

- 模板：保守 / 平衡 / 激进 / 自定义目标权重
- 平衡型默认大类目标：

| 大类 | 目标权重 |
|------|----------|
| 股票型 | 40% |
| 债券型 | 30% |
| 货币/理财 | 15% |
| QDII/海外 | 10% |
| 其他 | 5% |

- 触发：`｜当前权重 − 目标权重｜ > 5%` → 加/减仓信号；距上次再平衡 > 365 天 → 强制检查
- 输出示例：「债券低配 6.2%，建议增配 ¥X」

#### 层 2：风险/集中度（权重 30%）

| 规则 | 默认阈值 | 信号 |
|------|----------|------|
| 单只占比过高 | > 25% | 减仓 |
| 同源暴露 | 相关系数 > 0.85 | 合并/减一只 |
| 行业集中 | 单行业 > 40% | 分散警告 |
| 7 日内赎回费 | 持有 < 7 天 | 阻止卖出 |

#### 层 3：业绩质量（权重 30%）

基于 T+1 官方净值（不用盘中实时估值）：

| 指标 | 条件 | 信号 |
|------|------|------|
| 相对基准 | 1 年超额 < −5% | 观察/减仓 |
| 最大回撤 | > 同类 75 分位 | 风险警告 |
| 夏普比率 | < 同类中位数 | 质量偏低 |
| 基金经理变更 | 近 6 个月 | 观察标记 |

#### 综合输出格式

```
signal_type: reduce | add | hold | watch
strength: 1–5
score: -100 ~ +100（负=卖，正=买）
reasons: [{ layer, rule, detail }]
suggested_amount: ¥（基于目标权重反算）
```

**买入建议（v1）**：对低配大类输出「建议增配 ¥X 的 [大类名]」；不自动推荐具体基金代码（v1.1 加候选池）。

### 4. 数据同步策略

- **频率**：每日 20:00 后自动同步（净值更新后）；支持手动触发
- **内容**：净值序列、基准、基金类型/经理、季报 Top10 持仓
- **缓存**：`fund_metrics_cache` 避免重复计算
- **失败**：重试 3 次，指数退避；部分失败不阻塞已成功的基金

## 错误处理

| 场景 | 处理 |
|------|------|
| OCR 识别失败 | 返回原始文本 + 手动录入表单 |
| OCR 字段置信度低 | 标红，要求用户确认 |
| 基金代码无法匹配 | 模糊搜索基金名称，用户选择 |
| akshare 请求失败 | 展示上次成功数据 + 「数据可能过期」标记 |
| 净值缺失 | 跳过该只基金的业绩信号，概览仍展示持仓 |
| 持有天数未知 | 默认不触发 7 日赎回费规则 |
| 空持仓 | Dashboard 引导至 `/import` |

## 测试策略

| 层级 | 覆盖 |
|------|------|
| 单元测试 | 信号规则（给定权重/指标 → 预期 signal）；指标计算（夏普、回撤） |
| 集成测试 | OCR parser（fixture 截图 → 结构化 JSON）；数据 sync mock |
| API 测试 | 主要 REST 端点 happy path + 错误码 |
| E2E（可选 v1） | 上传 → 确认 → 查看 signals |

**Fixture**：保存脱敏截图样本（各 App 各 2 张）用于 OCR 回归。

## 分期交付

| 里程碑 | 内容 | 预估 |
|--------|------|------|
| M1 | 项目骨架 + OCR 导入 + 持仓 CRUD + 概览 | 1–2 周 |
| M2 | 数据同步 + 指标计算 + 再平衡信号 | 1 周 |
| M3 | 集中度 + 业绩信号 + 信号面板 | 1 周 |
| M4 | 策略参数 UI + 快照历史 + polish | 3–5 天 |

## 非功能需求

- **可复现**：相同持仓 + 相同策略参数 + 相同数据日期 → 相同信号
- **隐私**：v1 数据仅存本地 SQLite；截图不上传第三方（除非用户启用 Vision API）
- **性能**：100 只基金持仓，概览页 < 2s（含缓存）
- **演进**：Repository 层抽象，v2 换 PostgreSQL + 加 auth middleware 不改业务逻辑

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-21 | Agent + User | 初始版本，用户确认方案 A（量化 Lite） |
