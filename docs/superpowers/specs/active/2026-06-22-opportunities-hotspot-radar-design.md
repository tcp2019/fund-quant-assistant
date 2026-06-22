# v1.4 机会中心 + 热点雷达 设计规格

> **Status:** active
> **Created:** 2026-06-22
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Parent spec:** [2026-06-21-fund-quant-assistant-design.md](./2026-06-21-fund-quant-assistant-design.md)

## 目标

将分散在「买卖信号表格」「主题候选按钮」中的 actionable 信息，聚合为 **一眼可读的机会视图**：Dashboard 顶部展示今日该卖 / 该买 / 可探索摘要，并附带 **业绩驱动的热点主题雷达**；详情页 `/opportunities` 提供完整行动清单与主题排行。v1.4 不接入新闻 API；新闻摘要留 v1.4.1 / v1.5。

## 背景

v1.2–v1.3 已具备：量化信号引擎、大类/类内增配分配、akshare 候选基金、主题标签与主题候选。但用户打开 App 仍难以回答：

- 今天该卖哪几只？
- 该加仓哪几只（含具体金额）？
- 除持仓外，有哪些新基金/热点主题值得看？

根因：信号页为 30+ 行技术表格；候选基金默认折叠；Dashboard 无行动摘要；主题热点需逐块点击加载。

## 范围

### 包含（v1.4）

1. **`GET /api/opportunities`**：聚合 sell / add_holding / explore 行动项 + hot_themes
2. **`action_classifier`**：将 `signalActionType` 规则下沉到 backend（Python 为 source of truth）
3. **`theme_heat`**：基于 akshare open rank 计算各主题近 1 月收益中位数（Top 20 样本）
4. **Dashboard 摘要**：`ActionSummaryCards` + `HotThemeRadar`（各 Top 3 / Top 5）
5. **`/opportunities` 页面**：完整行动清单 + 热点雷达详情
6. **导航**：Layout 增加「机会」入口；摘要链到详情页 tab
7. **测试 + 文档**：单元/API 测试；主 spec 演进表更新

### 不包含

- 财经新闻 API / 要闻摘要（v1.4.1 / v1.5）
- 自动下单、持牌荐基话术
- 新 OCR 来源（与原主 spec v1.4 待定项解耦）
- LLM 自然语言解读
- Service Worker / 推送增强

### 后续（v1.4.1 / v1.5 预留）

- `HotThemeOut.news_headlines: list[str]` 字段占位
- 独立 `news_theme_mapper`：新闻标题 → 现有 `THEME_LABELS` 映射
- 热点雷达 UI 增加「相关要闻」折叠区

## 信息架构

```
Dashboard（/）
├── 【今日行动】ActionSummaryCards
│   ├── 🔴 建议卖出 · Top 3
│   ├── 🟢 持仓增配 · Top 3
│   └── 🔵 可考虑新买 · Top 3
├── 【热点雷达】HotThemeRadar · Top 5 强势主题
└── … 现有总览（大类/主题暴露/集中度/持仓表）不变 …

/opportunities
├── Tab: 行动清单
│   ├── 建议卖出（完整 Top 5+）
│   ├── 持仓增配（完整 Top 5+）
│   └── 探索新买（大类缺口 + 热点交叉）
└── Tab: 热点雷达
    └── 全主题排行 + 组合暴露 + 候选基金
```

## 架构

### 数据流

```
SignalRecord + Holding + strategy rebalance context
        ↓
action_classifier.classify(record, reasons) → sell | add_holding | explore | skip
        ↓
opportunities.build_actions() → sell_actions, buy_actions, explore_actions
        +
fund_rankings (open rank cache)
        ↓
theme_heat.compute_all() → heat_score per theme
        ↓
recommend_funds_by_theme() → candidates (exclude held)
        +
portfolio theme_allocation → portfolio_weight_pct, aligned_gap
        ↓
GET /api/opportunities → OpportunitiesOut
        ↓
Dashboard summary + OpportunitiesPage
```

### 新增模块

```
backend/app/services/signals/action_classifier.py
  - classify_signal_action(signal_type, reasons, suggested_amount, score) → str
  - is_sell_action / is_add_holding_action / is_explore_action helpers

backend/app/services/theme_heat.py
  - compute_theme_heat(session, theme_id) → heat_score, return_1m_median
  - rank_hot_themes(session, limit=9) → list[HotThemeRow]

backend/app/services/opportunities.py
  - build_opportunities(session, *, sell_limit, buy_limit, explore_limit, theme_limit) → OpportunitiesOut

backend/app/api/routes/opportunities.py
  - GET /api/opportunities

backend/app/schemas/opportunities.py
  - ActionItemOut, HotThemeOut, OpportunitiesOut
```

### API

**`GET /api/opportunities`**

Query（可选，均有默认值）：

| 参数 | 默认 | 说明 |
|------|------|------|
| `sell_limit` | 5 | 卖出行动条数 |
| `buy_limit` | 5 | 持仓增配条数 |
| `explore_limit` | 5 | 探索新买条数 |
| `theme_limit` | 5 | 热点主题条数（Dashboard 请求可传 3） |

Response:

```python
class ActionItemOut(BaseModel):
    action: Literal["sell", "add_holding", "explore"]
    fund_code: str = ""
    fund_name: str | None = None
    category: str | None = None
    category_label: str | None = None
    suggested_amount: float
    score: float
    strength: int = Field(ge=1, le=5)
    reason_summary: str
    signal_id: int | None = None
    candidates: list[FundCandidateOut] = []

class HotThemeOut(BaseModel):
    theme: str
    label: str
    heat_score: float
    return_1m_median: float | None = None
    portfolio_weight_pct: float = 0.0
    aligned_gap: bool = False
    aligned_category_label: str | None = None
    candidates: list[FundCandidateOut] = []

class OpportunitiesOut(BaseModel):
    snapshot_id: int | None
    data_as_of_date: str | None = None
    sell_actions: list[ActionItemOut]
    buy_actions: list[ActionItemOut]
    explore_actions: list[ActionItemOut]
    hot_themes: list[HotThemeOut]
```

每条对外展示的记录沿用 v1.2 红线：`candidates[]` 含 `data_source` + `as_of_date`；禁止静态 seed。

## 行动项规则

与前端 `signalDisplay.signalActionType` 对齐，**backend 为权威实现**；前端改为可选复用 API 分类结果或保持展示一致。

### 分类

| action | 条件 |
|--------|------|
| **skip → watch** | `purchase_limit` 层含 `redemption_hard_to_rebuy` / `purchase_limit_blocked` / `purchase_suspended` |
| **sell** | 分类后为 `reduce`，且 `suggested_amount < 0` |
| **add_holding** | 有 `fund_code`；分类后为 `add`（含 hold+rebalance 弱增配），且 `suggested_amount > 0` |
| **explore** | 无 `fund_code` 的大类增配信号；或热点主题 `aligned_gap=true` 且组合该主题占比低于阈值（见下） |

### 排序

| action | 排序键 |
|--------|--------|
| sell | `\|suggested_amount\|` ↓，其次 `\|score\|` ↓ |
| add_holding | `suggested_amount` ↓ |
| explore | 大类增配：`\|suggested_amount\|` ↓；热点交叉：`heat_score` ↓ |

### explore 候选

- **大类增配行**：复用 `recommend_funds(session, category, held_codes, limit=3)`
- **热点交叉**：复用 `recommend_funds_by_theme(session, theme_id, held_codes, limit=3)`

`reason_summary`：取首条 reason 格式化为 `{rule_label} · {detail}`，与 `summarizeReasons` 一致。

## 热点雷达（v1.4 业绩驱动）

### 热点评分

对每个 `theme_id ∈ THEME_LABELS`：

1. 从 `fetch_all_open_rankings(session)` 取 open rank 行
2. `filter_rankings_for_theme(session, theme_id, rows, exclude_codes=∅, limit=20, sort_by=return_1m)`
3. 若样本数 < 3：跳过该主题
4. `return_1m_median = median(return_1m of sample)`
5. `heat_score = return_1m_median`

按 `heat_score` 降序取 Top N。

### 组合暴露

- `portfolio_weight_pct`：来自 overview 的 `theme_allocation`（无则 0）
- `aligned_gap`：该主题映射的大类当前存在 **大类低配** rebalance 信号（`category_underweight`）

主题 → 大类映射（固定表，可扩展）：

| theme | 映射大类 |
|-------|----------|
| storage_semiconductor, cpo_optics, ai_compute, new_energy, healthcare, consumer, dividend | stock |
| gold | gold |
| qdii | qdii |
| （其余） | stock（默认） |

`aligned_category_label`：对应大类的中文标签（如「股票型」）。

### Dashboard vs 详情页

- Dashboard：`theme_limit=5`，候选每主题 Top 3
- 机会页热点 Tab：`theme_limit=9`（全主题），候选每主题 Top 3

## 前端

### 新增/变更

| 文件 | 说明 |
|------|------|
| `frontend/src/pages/OpportunitiesPage.tsx` | 双 Tab 详情页 |
| `frontend/src/components/ActionSummaryCards.tsx` | Dashboard 三卡摘要 |
| `frontend/src/components/HotThemeRadar.tsx` | 横向热点条 |
| `frontend/src/components/ActionList.tsx` | 分组行动列表（可展开） |
| `frontend/src/api/client.ts` | `fetchOpportunities()` |
| `frontend/src/types/index.ts` | Opportunities 类型 |
| `frontend/src/App.tsx` | 路由 `/opportunities` |
| `frontend/src/components/Layout.tsx` | 导航「机会」 |
| `frontend/src/pages/Dashboard.tsx` | 顶部嵌入摘要 + 雷达 |

### 空态文案

| 场景 | 文案 |
|------|------|
| 无快照 | 「导入持仓并同步后查看机会」+ 链到 /import |
| 无行动 | 「暂无明确行动，组合配置较为均衡」 |
| 热点不可用 | 「热点数据暂不可用，请稍后同步」 |
| 无 explore | 「暂无大类缺口或热点交叉机会」 |

### 合规

行动页与候选区沿用 v1.2 免责声明；热点区追加：

> 热点按主题基金近 1 月收益中位数排序，反映近期业绩而非新闻舆情，仅供参考，不构成投资建议。

## 错误处理

| 场景 | 行为 |
|------|------|
| 无 snapshot | `snapshot_id=null`，actions/themes 空列表 |
| akshare rank 失败 | `hot_themes=[]`，不伪造 heat_score |
| 某主题样本 < 3 | 跳过，不进入排行 |
| catalog 未就绪 | 主题候选为空列表；不影响 action 聚合 |
| signal 记录 reasons JSON 损坏 | 当作空 reasons，仍参与分类 fallback |

## 测试策略

| 用例 | 断言 |
|------|------|
| reduce + 负金额 | 进入 sell_actions |
| 类内增配不同金额 | add_holding 按金额降序 |
| purchase_limit 保护 | 不出现在 sell/add，或标记 watch 排除 |
| 大类增配无 fund_code | explore + candidates |
| theme heat 中位数 | fixture rank 下顺序正确 |
| aligned_gap | 股票低配 + semiconductor 主题 → aligned_gap=true |
| GET /api/opportunities | 200 + schema 校验 |
| Dashboard 空态 | 无 snapshot 时引导文案 |

pytest 中 mock akshare（与 `test_api_funds` 一致）；使用现有 rank fixture JSON。

## 与现有页面的关系

- **信号页**：保留完整技术表格，供深度排查；机会页为 **行动导向** 视图，不替代信号页
- **分析页**：相关性/风险不变；主题探索按钮可链到 `/opportunities?tab=themes`
- **ThemeExposurePanel**：Dashboard 仍保留；热点雷达为 **跨主题排行**，与之互补

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-22 | Agent | 已交付：GET /api/opportunities、Dashboard 行动摘要、/opportunities 页面、热点雷达 |
