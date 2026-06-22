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
| v1.0.1 | 支付宝 OCR 多格式、A 股盈亏配色 |
| v1.1 | Dashboard 大类/集中度、导入体验、导入后同步闭环 |
| v1.1.1 | Dashboard 大类/集中度图表分类配色（`chartColors`） |
| v1.2 | 候选基金（akshare 排行）、基金搜索、浏览器通知 — [设计规格](specs/active/2026-06-21-v12-recommendations-notifications-design.md) |
| v1.2.1 | 主题暴露、申购限购保护、定时 sync、持仓重估、同类排名业绩信号 — 见主 spec §5 |
| v1.3 | 类内目标权重增配分配 — [设计规格](specs/active/2026-06-22-intra-category-rebalance-allocation-design.md) |
| v1.4 | 浏览器通知增强、更多 OCR 来源（待定） |
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
fund_metadata(code, name, type, category, benchmark_code, manager,
             purchase_status, purchase_min_amount, daily_purchase_limit,
             themes_json, user_themes_json)
fund_nav_history(code, date, nav, acc_nav)
fund_metrics_cache(code, date, sharpe_1y, max_drawdown_1y, excess_return_1y,
                   return_1y, peer_return_percentile_3m, computed_from)
fund_catalog(code, name, fund_type, pinyin_abbr, synced_at)
fund_rank_cache(id, category, payload_json, fetched_at)
portfolio_metrics(snapshot_id, date, total_value, volatility, sharpe, max_dd, ...)
correlation_matrix(snapshot_id, date, matrix_json)
signals(id, snapshot_id, fund_code, signal_type, score, strength,
        reasons_json, suggested_amount, created_at)
strategy_config(id, template_name, target_weights_json, thresholds_json)
ocr_jobs(id, status, image_paths, parsed_json, confirmed_at)
```

`GET /api/portfolio/overview` 额外返回 `theme_allocation[]`（主题暴露，v1.2.1）。

### API 概要

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/ocr/upload` | 上传截图，返回解析草稿 |
| POST | `/api/ocr/{job_id}/confirm` | 确认 OCR 结果，创建快照 |
| GET | `/api/portfolio/overview` | 当前概览（含大类配置、Top5 集中度） |
| GET | `/api/portfolio/holdings` | 持仓明细 |
| GET | `/api/signals` | 信号列表（按 score 排序；大类增配附加 `candidates[]`） |
| GET | `/api/funds/search` | 基金目录搜索（Import 补代码） |
| POST | `/api/funds/catalog/refresh` | 手动刷新基金目录 |
| GET | `/api/funds/themes` | 主题列表 |
| GET | `/api/funds/themes/{theme_id}/candidates` | 主题候选基金（akshare 排行） |
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
| `/signals` | 买卖信号（SignalsTable：筛选 tab + 展开详情/候选） |
| `/analysis` | 相关性、行业暴露、风险指标 |
| `/settings` | 目标配置、规则阈值、数据同步 |

### 前端展示约定（v1.0.1）

- 金额/百分比格式化抽至 `frontend/src/utils/format.ts`、`profitLoss.ts`
- **A 股配色**：涨/盈利红色（`text-rose-600`），跌/亏损绿色（`text-emerald-600`）
- 盈亏金额不带正负号，方向由颜色表达；收益率保留 `+` 前缀

## 功能详述

### 1. 截图 OCR 导入

**支持来源（v1）**：支付宝、天天基金、腾讯理财通。

**识别字段**：基金名称/代码、持有份额、成本价、当前市值、持有收益、收益率。

**支付宝多格式解析（v1.0.1）**：同一平台 parser 按内容自动选择子策略，优先级为 Tab 导出 → 合并行导出 → 详情块 → 列表占比视图。

| 格式 | 典型来源 | 可识别字段 | 缺失字段 |
|------|----------|------------|----------|
| 详情块 | 单只基金详情页 OCR | 代码、份额、成本、市值、收益、收益率 | — |
| 列表占比 | 持仓列表页 OCR（单行合并） | 名称、市值、持有收益、收益率 | 代码、份额（需人工补） |
| 合并行导出 | 用户复制「名称 代码 市值 收益率」 | 代码、名称、市值、收益率（反推成本/收益） | 份额 |
| Tab 导出 | 表格复制（`\t` 分隔） | 代码、名称、市值、收益率 | 份额 |

**基础解析工具**：`parse_money`（千分位/`|` 分隔金额）、`strip_fund_name`（去标签噪声）、`extract_fund_code`（忽略金额尾部误匹配，如 `6,217730.00`）。

**流程**：
1. 用户上传 1–N 张截图，或粘贴 OCR 文本 / 表格导出
2. OCR + 布局模板匹配（按 App 分 parser，支付宝内部再分格式）
3. 展示可编辑确认页；缺代码/份额行高亮，可删行；收益率以百分比编辑
4. 零条解析结果时前端提示检查平台与内容
5. 确认后创建快照；导入成功页提供「同步数据并查看信号」

**校验**：
- 市值必须 > 0；无基金代码或份额时标黄警告，**不阻断**导入（列表/导出格式常见）
- 有份额且成本价 > 0 时：市值/份额与成本价偏差 > 50% 标黄警告

### 2. 持仓概览

| 模块 | 内容 |
|------|------|
| 总览 | 总市值、总成本、总盈亏、收益率 |
| 大类配置 | Dashboard 环形饼图（`category_allocation`）+ 图例 |
| 主题暴露 | Dashboard / Analysis `ThemeExposurePanel`（`theme_allocation`，v1.2.1） |
| 集中度 | Dashboard Top5 进度条 + `concentration_top5_pct` 汇总卡 |
| 持仓表 | 权重%、成本、现价、浮盈、主题标签（`ThemeTags`，按权重降序） |
| 深度分析 | Analysis 页：相关性矩阵、波动率/夏普/回撤、主题暴露 |

**Dashboard 可视化样式（v1.1.1）**

- 共享分类色板：`frontend/src/utils/chartColors.ts`（8 色：indigo / sky / emerald / amber / pink / violet / teal / orange），按类别或排名循环取色，避免全 slate 灰阶导致图表发闷
- **大类配置**：Recharts 环形饼图 + 双色点图例；占比数字 `tabular-nums`、semibold
- **集中度 Top5**：合计占比卡 `indigo→sky` 浅渐变底 + 边框；每只 Top 持仓进度条使用与饼图相同的 `chartColor(index)`，便于扫读排名差异

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
| 同类排名 | 近 3 月收益百分位 < 25%（且无超额信号时） | 观察 |
| 最大回撤 | 1 年 < −20%（固定阈值；Future：同类分位） | 风险警告 |
| 夏普比率 | < 0.5 | 质量偏低 |
| 基金经理变更 | 近 6 个月 | 观察标记（Future） |

#### 综合输出格式

```
signal_type: reduce | add | hold | watch
strength: 1–5
score: -100 ~ +100（负=卖，正=买）
reasons: [{ layer, rule, detail }]
suggested_amount: ¥
```

**建议金额（v1.3）**

| 层级 | 计算方式 |
|------|----------|
| 大类增配（`fund_code=""`） | 目标大类权重反算缺口（如 ¥52,806） |
| 单只持仓增配 | 按类内目标权重缺口比例分配大类缺口；业绩偏弱基金不参与（¥0） |
| 单只减仓 | 集中度层暂未写入金额；再平衡减配见大类信号 |

类内目标默认 **等权**（Settings 可切换「按现占比」）。详见 [v1.3 规格](specs/active/2026-06-22-intra-category-rebalance-allocation-design.md)。

**买入建议**：对低配大类输出「建议增配 ¥X 的 [大类名]」；v1.2 起大类信号附加 akshare 公开排行候选（见 [v1.2 规格](specs/active/2026-06-21-v12-recommendations-notifications-design.md)）。

**申购限购保护（v1.2.1）**：sync 写入 `fund_metadata` 申购状态与日限购；信号引擎对「日限购 ≤ ¥500」的基金：增配降级为观察并 cap 金额；无业绩触发的减仓在限购下暂不建议卖出（难买回）。

### 4. 数据同步策略

- **频率**：每日 20:05（Asia/Shanghai）APScheduler 自动 sync（可 `auto_sync_enabled` 关闭）；支持 Settings 手动触发
- **内容**：净值序列、基准、基金类型/经理、申购限购（`fund_purchase_em`）、主题标签、同类排名百分位、季报 Top10 持仓（Future）
- **sync 后链路**：拉净值/metadata → 写 `FundMetricsCache` → 重估持仓市值（`holdings_revalue`）→ 跑信号引擎
- **缓存**：`fund_metrics_cache`、`fund_catalog`、`fund_rank_cache` 避免重复计算/请求
- **失败**：`http_retry` 指数退避重试；部分失败不阻塞已成功的基金

### 5. v1.2.1 增量能力

#### 主题暴露与候选

- **打标**：`fund_themes.detect_themes` 按基金名称/类型关键词匹配（半导体、CPO、AI、新能源等）；结果存 `fund_metadata.themes_json`
- **暴露汇总**：`GET /api/portfolio/overview` → `theme_allocation[]`；Dashboard / Analysis 展示 `ThemeExposurePanel`
- **主题候选**：`GET /api/funds/themes/{id}/candidates` 从 akshare 全市场排行按主题过滤，排序字段 `return_1m | return_1w | return_1y`

#### 同类排名指标

- sync 时 `peer_metrics.fetch_peer_return_percentile_3m` 写入 `FundMetricsCache.peer_return_percentile_3m`
- 业绩层在无超额收益数据时，用同类排名后 25% 触发观察信号

#### 申购限购

- 数据源：akshare `fund_purchase_em`
- 规则见 §3 信号引擎「申购限购保护」；reasons 层 `purchase_limit`

#### 定时任务

- `main.py` lifespan 注册 `run_scheduled_sync`：sync → revalue → `run_signal_engine`
- 配置：`config.auto_sync_enabled`（默认 true）、`auto_sync_hour=20`、`auto_sync_minute=5`

## 错误处理

| 场景 | 处理 |
|------|------|
| OCR 识别失败 | 返回原始文本 + 手动录入表单 |
| OCR 零条解析 | 前端提示检查平台选择与粘贴内容格式 |
| OCR 字段置信度低 | 标黄/标红，要求用户确认；缺代码/份额可补全后入库 |
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

**Fixture**：保存脱敏 OCR 文本样本用于 parser 回归。支付宝除 `alipay_sample.txt`（详情块）外，另含 `alipay_list_sample.txt`（列表占比）、`alipay_merged_sample.txt`（合并行）、`alipay_tab_export_sample.txt`（Tab 导出）。

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
| 2026-06-21 | Agent | v1.0.1：支付宝 OCR 多格式解析、校验放宽、A 股盈亏配色与格式化工具 |
| 2026-06-21 | Agent | v1.1：Dashboard 大类/Top5、导入行级警告与删行、导入后同步闭环 |
| 2026-06-21 | Agent + User | v1.2 规格：akshare 真实候选/搜索/通知，见独立 design doc |
| 2026-06-21 | Agent | v1.1.1：Dashboard 大类饼图与 Top5 集中度改用 `chartColors` 分类色板，Top5 汇总卡 indigo/sky 强调 |
| 2026-06-22 | Agent | 文档同步 v1.2.1：主题暴露、限购、定时 sync、重估、业绩同类排名；API/模型补全 |
| 2026-06-22 | Agent | v1.3 类内目标权重增配分配已交付 |
