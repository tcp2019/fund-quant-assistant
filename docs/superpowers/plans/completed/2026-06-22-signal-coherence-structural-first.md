# v1.6 信号一致性 · 结构优先 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** completed
> **Created:** 2026-06-22
> **Spec:** docs/superpowers/specs/active/2026-06-22-signal-coherence-structural-first-design.md
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Based on:** v1.5 组合管理基础 · Red Team 审查

**Goal:** Consolidation 阻断类内增配、强制审视改为提醒信号、机会中心/Dashboard 结构待办与交易行动分层展示。

**Architecture:** 在 `engine` 引入 `overcrowded_categories` 集合阻断 `_build_category_add_amounts`；`rebalance` 拆分审视提醒为独立函数并移除 threshold=0；`opportunities` 聚合 `structural_actions`；前端 Dashboard/机会页增加结构区 UI。

**Tech Stack:** Python 3.11, FastAPI, SQLModel, pytest | React, TypeScript, Tailwind

---

## 文件结构

| 文件 | 职责 |
|------|------|
| `backend/app/services/signals/rebalance.py` | 移除 force threshold=0；新增 `compute_rebalance_review_signals` |
| `backend/app/services/signals/engine.py` | overcrowded 阻断增配；append review signals |
| `backend/app/services/signals/action_classifier.py` | `consolidation_blocked_add` → watch |
| `backend/app/services/opportunities.py` | 构建 `structural_actions` |
| `backend/app/schemas/opportunities.py` | `StructuralActionOut` |
| `backend/tests/test_consolidation_block.py` | 阻断逻辑单元测试（新建） |
| `backend/tests/test_rebalance_force.py` | 更新为新审视语义 |
| `backend/tests/test_api_opportunities.py` | structural_actions API 测试 |
| `frontend/src/types/index.ts` | `StructuralAction` 类型 |
| `frontend/src/components/StructuralAlerts.tsx` | 结构待办横幅（新建） |
| `frontend/src/components/ActionSummaryCards.tsx` | 嵌入 StructuralAlerts |
| `frontend/src/pages/OpportunitiesPage.tsx` | 结构问题区块 + 增配说明 |

---

### Task 1: 强制审视 — 移除 threshold=0，新增 review 信号

**Files:**
- Modify: `backend/app/services/signals/rebalance.py`
- Modify: `backend/tests/test_rebalance_force.py`
- Create: `backend/tests/test_rebalance_review.py`

- [ ] **Step 1: 写失败测试 — force_review 不再改变 rebalance 交易信号**

```python
# backend/tests/test_rebalance_review.py
from app.schemas.settings import DEFAULT_TEMPLATES
from app.services.signals.rebalance import (
    compute_rebalance_review_signals,
    compute_rebalance_signals,
)


def test_force_review_does_not_change_rebalance_trades():
    category_weights = {
        "stock": 0.42,
        "bond": 0.28,
        "money": 0.15,
        "qdii": 0.10,
        "other": 0.05,
    }
    target = DEFAULT_TEMPLATES["balanced"]
    normal = compute_rebalance_signals(
        category_weights, target, total_value=10000, threshold_pct=5.0, force_review=False
    )
    forced = compute_rebalance_signals(
        category_weights, target, total_value=10000, threshold_pct=5.0, force_review=True
    )
    assert normal == forced


def test_review_signals_within_band_only():
    category_weights = {"stock": 0.42, "bond": 0.28, "money": 0.15, "qdii": 0.10, "other": 0.05}
    target = DEFAULT_TEMPLATES["balanced"]
    reviews = compute_rebalance_review_signals(
        category_weights, target, total_value=10000, threshold_pct=5.0, force_review=True
    )
    assert len(reviews) >= 1
    bond = next(s for s in reviews if s["category"] == "bond")
    assert bond["signal_type"] == "watch"
    assert bond["rule"] == "rebalance_review_due"
    assert bond["suggested_amount"] == 0.0


def test_review_skipped_when_force_review_false():
    category_weights = {"stock": 0.42, "bond": 0.28}
    target = DEFAULT_TEMPLATES["balanced"]
    assert (
        compute_rebalance_review_signals(
            category_weights, target, 10000, 5.0, force_review=False
        )
        == []
    )
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd backend && pytest tests/test_rebalance_review.py -v`
Expected: FAIL — `compute_rebalance_review_signals` not defined; `test_rebalance_force` may still pass old behavior

- [ ] **Step 3: 实现 rebalance 变更**

```python
# backend/app/services/signals/rebalance.py — compute_rebalance_signals 内删除：
#   effective_threshold = 0.0 if force_review else threshold_pct
# 改为始终：
#   effective_threshold = threshold_pct
# force_review 参数可保留为向后兼容但不再使用（或删除参数并在 engine 单独传）

def compute_rebalance_review_signals(
    category_weights: dict[str, float],
    target: dict[str, float],
    total_value: float,
    threshold_pct: float,
    *,
    force_review: bool,
) -> list[dict]:
    if not force_review:
        return []
    categories = set(category_weights) | set(target)
    signals: list[dict] = []
    for category in sorted(categories):
        current = category_weights.get(category, 0.0)
        target_weight = target.get(category, 0.0)
        deviation_pct = round((target_weight - current) * 100, 2)
        if deviation_pct == 0 or abs(deviation_pct) > threshold_pct:
            continue
        label = CATEGORY_LABELS.get(category, category)
        signals.append(
            {
                "category": category,
                "signal_type": "watch",
                "rule": "rebalance_review_due",
                "deviation_pct": deviation_pct,
                "suggested_amount": 0.0,
                "detail": (
                    f"年度审视：{label}偏离 {abs(deviation_pct):.1f}%"
                    f"（在 {threshold_pct:.0f}% 带宽内），建议关注"
                ),
            }
        )
    return signals
```

- [ ] **Step 4: 更新 `test_rebalance_force.py` 为 deprecated 或替换**

```python
# 删除 test_force_review_triggers_small_deviation 或改为：
def test_force_review_no_longer_triggers_trades():
    ...  # 与 test_force_review_does_not_change_rebalance_trades 相同断言
```

- [ ] **Step 5: 运行测试**

Run: `cd backend && pytest tests/test_rebalance_review.py tests/test_rebalance_force.py -v`
Expected: PASS

---

### Task 2: Engine 接入 review 信号

**Files:**
- Modify: `backend/app/services/signals/engine.py`
- Test: `backend/tests/test_rebalance_review.py`

- [ ] **Step 1: 写失败测试 — review 信号写入 aggregate 结果**

```python
# 追加到 test_rebalance_review.py
from app.services.signals.engine import append_review_signals


def test_append_review_signals_adds_category_watch_rows():
    reviews = [
        {
            "category": "bond",
            "signal_type": "watch",
            "rule": "rebalance_review_due",
            "detail": "年度审视：债券型偏离 2.0%（在 5% 带宽内），建议关注",
            "suggested_amount": 0.0,
        }
    ]
    results = append_review_signals([], reviews)
    assert len(results) == 1
    assert results[0]["fund_code"] == ""
    assert results[0]["reasons"][0]["rule"] == "rebalance_review_due"
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && pytest tests/test_rebalance_review.py::test_append_review_signals_adds_category_watch_rows -v`

- [ ] **Step 3: 在 engine.py 添加 `append_review_signals`（镜像 `append_consolidation_signals`）并在 `run_signal_engine` 调用**

```python
def append_review_signals(results: list[dict], review: list[dict]) -> list[dict]:
    for signal in review:
        label = CATEGORY_LABELS.get(signal["category"], signal["category"])
        score = round(_layer_contribution("watch", LAYER_WEIGHTS["rebalance"], 0.5), 2)
        results.append(
            {
                "fund_code": "",
                "category": signal["category"],
                "signal_type": "watch",
                "score": score,
                "strength": _score_to_strength(score),
                "reasons": [
                    {
                        "layer": "rebalance",
                        "rule": "rebalance_review_due",
                        "detail": signal["detail"],
                        "category": signal["category"],
                        "category_label": label,
                    }
                ],
                "suggested_amount": 0.0,
                "category_label": label,
            }
        )
    return results
```

在 `run_signal_engine` 中：

```python
from app.services.signals.rebalance import compute_rebalance_review_signals

review = compute_rebalance_review_signals(
    dict(category_weights), target, total_value,
    thresholds["rebalance_deviation_pct"],
    force_review=force_review,
)
...
aggregated = append_consolidation_signals(aggregated, consolidation)
aggregated = append_review_signals(aggregated, review)
```

- [ ] **Step 4: 运行测试**

Run: `cd backend && pytest tests/test_rebalance_review.py -v`
Expected: PASS

---

### Task 3: Consolidation 阻断类内增配

**Files:**
- Modify: `backend/app/services/signals/engine.py`
- Modify: `backend/app/services/signals/action_classifier.py`
- Create: `backend/tests/test_consolidation_block.py`

- [ ] **Step 1: 写失败测试 — overcrowded 大类单只增配为 0**

```python
# backend/tests/test_consolidation_block.py
from app.services.signals.engine import aggregate_signals


def test_overcrowded_category_blocks_intra_add_amounts():
    rebalance = [
        {
            "category": "stock",
            "signal_type": "add",
            "deviation_pct": 9.1,
            "suggested_amount": 10000.0,
            "detail": "股票型低配 9.1%",
        }
    ]
    fund_categories = {f"S{i:02d}": "stock" for i in range(12)}
    market_value_by_code = {code: 1000.0 for code in fund_categories}
    overcrowded = {"stock"}

    results = aggregate_signals(
        rebalance,
        [],
        [],
        fund_categories,
        market_value_by_code=market_value_by_code,
        total_value=12000.0,
        category_targets={"stock": 0.4},
        intra_category_mode="equal",
        overcrowded_categories=overcrowded,
    )
    fund_results = [r for r in results if r["fund_code"]]
    assert all(r["suggested_amount"] == 0.0 for r in fund_results)
    assert any(
        reason.get("rule") == "consolidation_blocked_add"
        for r in fund_results
        for reason in r["reasons"]
    )
    category_adds = [r for r in results if not r["fund_code"] and r["signal_type"] == "add"]
    assert len(category_adds) == 1
    assert category_adds[0]["suggested_amount"] == 10000.0
```

- [ ] **Step 2: 运行确认失败**

Run: `cd backend && pytest tests/test_consolidation_block.py -v`

- [ ] **Step 3: 实现 engine 变更**

1. `aggregate_signals` 增加参数 `overcrowded_categories: set[str] | None = None`
2. 在 `_build_category_add_amounts` 返回后，对 `category in overcrowded_categories` 的 fund codes 将 `amounts[code] = 0` 并记录 blocked set
3. 在 reasons 循环中追加 `consolidation_blocked_add`
4. `run_signal_engine`：

```python
consolidation = compute_consolidation_signals(...)
overcrowded_categories = {s["category"] for s in consolidation}
aggregated = aggregate_signals(..., overcrowded_categories=overcrowded_categories)
```

- [ ] **Step 4: action_classifier 测试与实现**

```python
# test_consolidation_block.py
from app.services.signals.action_classifier import classify_signal_action

def test_consolidation_blocked_not_add_holding():
    reasons = [
        {"layer": "rebalance", "rule": "category_underweight", "detail": "..."},
        {"layer": "aggregate", "rule": "consolidation_blocked_add", "detail": "..."},
    ]
    assert classify_signal_action("add", reasons, 1000.0, 25.0) == "watch"
```

```python
# action_classifier.py
def _consolidation_blocked_add(reasons: list[dict]) -> bool:
    return any(reason.get("rule") == "consolidation_blocked_add" for reason in reasons)

# 在 classify_signal_action add 分支与 performance_blocked 并列检查
```

- [ ] **Step 5: 运行测试**

Run: `cd backend && pytest tests/test_consolidation_block.py -v`
Expected: PASS

---

### Task 4: Opportunities API — structural_actions

**Files:**
- Modify: `backend/app/schemas/opportunities.py`
- Modify: `backend/app/services/opportunities.py`
- Modify: `backend/tests/test_api_opportunities.py`（或新建）

- [ ] **Step 1: 写失败 API 测试**

```python
def test_opportunities_includes_structural_actions(client, seeded_overcrowded_snapshot):
    resp = client.get("/api/opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert "structural_actions" in data
    assert any(a["action"] == "consolidate" for a in data["structural_actions"])
```

（若无可复用 fixture，在测试内 POST snapshot + 12 只 stock holdings + sync）

- [ ] **Step 2: 实现 schema**

```python
class StructuralActionOut(BaseModel):
    action: Literal["consolidate", "rebalance_review"]
    category: str
    category_label: str
    detail: str
    fund_count: int | None = None
    blocked_buy_count: int | None = None

class OpportunitiesOut(BaseModel):
    ...
    structural_actions: list[StructuralActionOut] = Field(default_factory=list)
```

- [ ] **Step 3: 实现 `build_opportunities` 提取逻辑**

```python
STRUCTURAL_RULE_MAP = {
    "category_overcrowded": "consolidate",
    "rebalance_review_due": "rebalance_review",
}

def _build_structural_actions(records, holdings_by_category) -> list[StructuralActionOut]:
    ...
```

对 `consolidate`：`fund_count` 来自 signal reason 或 holdings 计数；`blocked_buy_count` 统计同 category 含 `consolidation_blocked_add` 的单只 record 数。

- [ ] **Step 4: 运行 API 测试**

Run: `cd backend && pytest tests/test_api_opportunities.py -v`

---

### Task 5: 前端类型与 StructuralAlerts 组件

**Files:**
- Modify: `frontend/src/types/index.ts`
- Create: `frontend/src/components/StructuralAlerts.tsx`
- Modify: `frontend/src/components/ActionSummaryCards.tsx`
- Modify: `frontend/src/pages/OpportunitiesPage.tsx`

- [ ] **Step 1: 添加 TypeScript 类型**

```typescript
export interface StructuralAction {
  action: 'consolidate' | 'rebalance_review'
  category: string
  category_label: string
  detail: string
  fund_count?: number | null
  blocked_buy_count?: number | null
}

export interface OpportunitiesOut {
  ...
  structural_actions: StructuralAction[]
}
```

- [ ] **Step 2: 创建 `StructuralAlerts.tsx`**

- 琥珀色边框卡片列表
- `consolidate` 图标 📦，`rebalance_review` 图标 📋
- 展示 `detail` + 可选 `blocked_buy_count` 文案

- [ ] **Step 3: Dashboard — `ActionSummaryCards` 顶部渲染 `<StructuralAlerts items={data.structural_actions} />`**

- [ ] **Step 4: OpportunitiesPage — actions tab 顶部结构区；若 `structural_actions` 含 consolidate 且 `buy_actions.length > 0`，增配区上方显示说明文案**

- [ ] **Step 5: 手动验证**

Run frontend dev server，导入 12+ 同大类持仓，sync，确认 Dashboard 结构横幅 + 机会页分区。

---

### Task 6: 文档同步

**Files:**
- Modify: `docs/superpowers/specs/active/2026-06-21-fund-quant-assistant-design.md`（演进表加 v1.6 行）
- Modify: `docs/superpowers/specs/active/2026-06-22-portfolio-management-foundation-design.md`（A3 强制审视语义脚注）
- Modify: `docs/superpowers/README.md`（功能索引）

- [ ] **Step 1: 主 spec 演进表增加 v1.6 链接**
- [ ] **Step 2: v1.5 spec A3 注明「v1.6 已改为审视提醒，见 signal-coherence spec」**
- [ ] **Step 3: README 索引表增加 v1.6 行**

---

### Task 7: 全量验证

- [ ] **Step 1: 运行后端全量测试**

Run: `cd backend && pytest tests -v`
Expected: all pass

- [ ] **Step 2: 31 只股基 Red Team 场景回归（可选脚本）**

确认 `buy_actions` 为 0，`structural_actions` 含 consolidate，大类 explore 仍可用。

- [ ] **Step 3: Plan 完成后移入 `plans/completed/` 并更新 Status**

---

## Spec 覆盖自检

| Spec 章节 | Task |
|-----------|------|
| A1–A5 Consolidation 阻断 | Task 3 |
| B1–B4 强制审视 | Task 1, 2 |
| C1–C5 机会中心 UI | Task 4, 5 |
| 测试策略 | 各 Task 内测试 |
| 文档 | Task 6 |

## 执行选项

Plan 已保存至 `docs/superpowers/plans/active/2026-06-22-signal-coherence-structural-first.md`。

**1. Subagent-Driven（推荐）** — 每 Task 独立 subagent，逐 Task 审查

**2. Inline Execution** — 本会话按 Task 顺序直接实现，检查点验收

请选择执行方式。
