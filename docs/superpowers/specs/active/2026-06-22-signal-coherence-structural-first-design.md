# v1.6 信号一致性 · 结构优先 设计规格

> **Status:** active
> **Created:** 2026-06-22
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Parent spec:** [2026-06-21-fund-quant-assistant-design.md](./2026-06-21-fund-quant-assistant-design.md)
> **Builds on:** [v1.5 组合管理基础](./2026-06-22-portfolio-management-foundation-design.md) · [v1.4 机会中心](./2026-06-22-opportunities-hotspot-radar-design.md)
> **Based on:** Red Team 审查（31 只持仓推演 + 2022–2024 熊市误触发分析）

## 目标

消除 **「结构问题 vs 交易建议」** 的矛盾输出：当大类持仓过多（Consolidation）时不应同时给出大量类内增配；强制再平衡审视不应把带宽降为 0 导致过度交易。在机会中心与 Dashboard 将 **结构待办** 与 **可执行交易** 分层展示。

## 背景（Red Team 结论摘要）

| 问题 | 现状 | 期望 |
|------|------|------|
| 31 只股基 + Consolidation watch | 仍输出 14 条 `add_holding` | 先合并，暂停类内增配 |
| `force_review → threshold=0` | ±1% 偏离也产生交易金额 | 审视 = 提醒，非强制交易 |
| 机会中心 | 仅 sell / buy / explore | 增加「结构问题」区 |

## 范围

### 包含（v1.6）

#### A — Consolidation 阻断类内增配

| 项 | 说明 |
|----|------|
| A1 阻断规则 | 大类 `len(holdings) > max_funds_per_category` → 该大类 **单只** `suggested_amount` 增配归零 |
| A2 大类信号保留 | 大类行（`fund_code=""`）仍保留缺口金额与候选，供 explore / 信息参考 |
| A3 reason | 受影响单只追加 `consolidation_blocked_add`（performance 层或 aggregate 层均可，统一 rule 名） |
| A4 action_classifier | `consolidation_blocked_add` → 不进 `add_holding`，等同 `watch` |
| A5 减配不受影响 | 超配大类减配分配逻辑不变 |

#### B — 强制审视改语义

| 项 | 说明 |
|----|------|
| B1 移除 bandwidth=0 | `compute_rebalance_signals` **不再**因 `force_review` 将 `effective_threshold` 设为 0 |
| B2 审视提醒信号 | 新增 `compute_rebalance_review_signals`：当 `force_review=True` 且 `0 < \|deviation\| ≤ threshold` 时输出大类级 `watch`，rule=`rebalance_review_due` |
| B3 超带宽行为不变 | `\|deviation\| > threshold` 仍正常产生 add/reduce 与金额 |
| B4 文档 | 主 spec §3 再平衡「365 天强制检查」改为「强制审视提醒」 |

#### C — 机会中心结构分层

| 项 | 说明 |
|----|------|
| C1 API | `GET /api/opportunities` 增加 `structural_actions[]` |
| C2 结构项类型 | `consolidate`（category_overcrowded）、`rebalance_review`（rebalance_review_due） |
| C3 Dashboard | `ActionSummaryCards` 上方增加「结构待办」横幅（有则显示，优先于交易卡片） |
| C4 机会页 | Tab「行动清单」顶部增加「结构问题」区块；有结构阻断时，持仓增配区显示说明文案 |
| C5 前端类型 | `OpportunitiesOut` / `StructuralAction` 类型同步 |

### 不包含（Future）

- 弱基清仓通道（performance reduce + 小仓位 → 独立 sell 建议）→ v1.7
- 被动/指数基业绩规则分化 → v1.7
- 部分再平衡系数 `rebalance_fraction` → v1.7
- 基金分类穿透（季报仓位）→ v2
- 自动合并推荐（「保留哪 8 只」）→ Future

## A1 阻断算法

在 `run_signal_engine` 聚合流程中，**Consolidation 判定先于类内增配分配生效**：

```
overcrowded_categories = {s.category for s in consolidation}
```

在 `_build_category_add_amounts` 或分配完成后：

```
for code in category funds where category in overcrowded_categories:
    suggested_amount[code] = 0
    append reason consolidation_blocked_add
```

大类增配行（`fund_code=""`）**不阻断**，`suggested_amount` 仍为整笔缺口。

## B2 审视提醒信号

```python
def compute_rebalance_review_signals(
    category_weights, target, total_value, threshold_pct, *, force_review: bool
) -> list[dict]:
    # force_review=False → []
    # 对每个 category:
    #   deviation_pct = (target - current) * 100
    #   if 0 < abs(deviation_pct) <= threshold_pct:
    #       watch, rule=rebalance_review_due,
    #       detail="年度审视：{label}偏离 {dev}%（在 {threshold}% 带宽内），建议关注"
```

写入 `SignalRecord` 方式与 Consolidation 相同：大类级 `fund_code=""`，`suggested_amount=0`。

## C1 API 扩展

```python
class StructuralActionOut(BaseModel):
    action: Literal["consolidate", "rebalance_review"]
    category: str
    category_label: str
    detail: str
    fund_count: int | None = None
    blocked_buy_count: int | None = None  # consolidate 时：该大类被阻断的增配条数

class OpportunitiesOut(BaseModel):
    ...
    structural_actions: list[StructuralActionOut] = []
```

`build_opportunities` 从 `SignalRecord` 提取：

- `rule=category_overcrowded` → `consolidate`
- `rule=rebalance_review_due` → `rebalance_review`

`blocked_buy_count`：统计同 snapshot 下该 category 含 `consolidation_blocked_add` 且原增配意图的单只信号数（可选，便于 UI 展示「已暂停 N 笔增配」）。

## 架构数据流（v1.6 变更点）

```
holdings + strategy + metrics + correlation
        ↓
compute_rebalance_signals (force_review 不再改 threshold)
        ↓
compute_rebalance_review_signals (force_review 时)
        ↓
consolidation → overcrowded_categories set
        ↓
intra_category add (skip/zero if overcrowded)
        ↓
aggregate → apply consolidation_blocked reasons
        ↓
append_consolidation + append_review_signals
        ↓
min_trade → purchase_limits → SignalRecord
        ↓
opportunities: structural_actions + sell/buy/explore
```

## UI 文案约定

| 场景 | 文案 |
|------|------|
| 结构横幅标题 | 结构待办 |
| consolidate | `{大类} 持仓 {n} 只，超过建议上限 {max} 只 — 建议先合并为核心持仓，再考虑增配` |
| rebalance_review | `{大类} 偏离 {x}%（在带宽内）— 年度审视提醒，暂无强制交易` |
| 增配区有阻断 | `以下增配已因持仓过多暂停；请先处理上方结构问题` |

Explore / 大类缺口候选 **保持**「浏览参考，非配置建议」标注，不受阻断影响。

## 错误处理

| 场景 | 行为 |
|------|------|
| 大类无持仓但 overcrowded（不应发生） | Consolidation 不触发 |
| 阻断后大类增配行仍在 | 预期行为；explore 仍可用 |
| 无 structural_actions | API 返回 `[]`；UI 不展示结构区 |
| 旧快照无新 rule | 重新 sync / run_signal_engine 后生成 |

## 测试策略

| 层级 | 用例 |
|------|------|
| 单元 | overcrowded 大类单只增配归零；非 overcrowded 不受影响；review 信号在带宽内；review 不触发超带宽 add；force_review 不再 threshold=0 |
| 集成 | `run_signal_engine` 31 只股基 → 0 add_holding（opportunities）；Consolidation + 大类 explore 仍在 |
| API | `/api/opportunities` 返回 `structural_actions` |
| 回归 | 更新 `test_rebalance_force.py` 断言为新语义 |

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-22 | Agent + User | 初始版本；Red Team 跟进 A/B/C 三工作流 |
| 2026-06-22 | Agent | 已交付：Consolidation 阻断增配、审视提醒、structural_actions API、Dashboard/机会页结构区 |
