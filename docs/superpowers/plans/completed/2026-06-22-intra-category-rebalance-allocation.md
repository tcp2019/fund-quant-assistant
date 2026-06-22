# v1.3 类内目标权重增配分配 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** completed
> **Created:** 2026-06-22
> **Spec:** docs/superpowers/specs/active/2026-06-22-intra-category-rebalance-allocation-design.md
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Based on:** docs/superpowers/plans/completed/2026-06-21-v12-recommendations-notifications.md

**Goal:** 将大类增配缺口从「同类均摊」改为按类内目标权重缺口比例分配，并用业绩层过滤不可增配基金。

**Architecture:** 新增 `signals/intra_category.py` 封装权重推导、缺口计算、归一分配；`aggregate_signals` 接收持仓市值与策略参数后调用；`StrategyConfig` 增加 `intra_category_mode` / `fund_target_weights_json`；Settings 暴露等权/按现占比切换。

**Tech Stack:** Python 3.11, FastAPI, SQLModel, pytest | React 18, TypeScript

---

## 文件结构

```
backend/
├── app/db/models.py                          # StrategyConfig +2 字段
├── app/db/session.py                         # SQLite ALTER 迁移
├── app/schemas/settings.py                   # StrategyOut/UpdateIn 扩展
├── app/api/routes/settings.py                # 读写新字段 + custom 校验
├── app/services/signals/intra_category.py    # 新建：核心算法
├── app/services/signals/engine.py            # aggregate_signals / run_signal_engine
├── tests/test_intra_category.py              # 新建：单元测试
└── tests/test_signals_engine.py              # 更新 aggregate 测试

frontend/
├── src/types/index.ts                        # StrategyConfig 扩展
├── src/pages/SettingsPage.tsx                # 类内分配模式下拉
└── src/api/client.ts                         # updateStrategy body 扩展

docs/superpowers/
├── specs/active/2026-06-21-fund-quant-assistant-design.md  # v1.3 交付后更新均摊描述
└── README.md                                 # plan active → completed
```

---

## Task 1: `intra_category.py` 核心算法（TDD）

**Files:**
- Create: `backend/app/services/signals/intra_category.py`
- Create: `backend/tests/test_intra_category.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_intra_category.py
from app.services.signals.intra_category import (
    allocate_category_add,
    compute_fund_gaps,
    is_performance_blocked_add,
    resolve_intra_category_weights,
)


def test_resolve_equal_weights():
    weights = resolve_intra_category_weights(
        "equal",
        {"A": "stock", "B": "stock", "C": "bond"},
        {"A": 1000.0, "B": 2000.0, "C": 500.0},
        category="stock",
        custom_weights=None,
    )
    assert weights == {"A": 0.5, "B": 0.5}


def test_resolve_pro_rata_weights():
    weights = resolve_intra_category_weights(
        "pro_rata",
        {"A": "stock", "B": "stock"},
        {"A": 1000.0, "B": 3000.0},
        category="stock",
        custom_weights=None,
    )
    assert abs(weights["A"] - 0.25) < 1e-9
    assert abs(weights["B"] - 0.75) < 1e-9


def test_compute_fund_gaps_equal_target():
    weights = {"A": 0.5, "B": 0.5}
    gaps = compute_fund_gaps(
        market_value_by_code={"A": 1000.0, "B": 4000.0},
        intra_weights=weights,
        total_value=10000.0,
        category_target=0.4,
    )
    # target mv each = 0.4 * 0.5 * 10000 = 2000
    assert gaps["A"] == 1000.0
    assert gaps["B"] == 0.0


def test_allocate_category_add_proportional():
    amounts = allocate_category_add(
        category_gap_amount=1000.0,
        fund_gaps={"A": 600.0, "B": 400.0},
    )
    assert amounts["A"] == 600.0
    assert amounts["B"] == 400.0


def test_allocate_category_add_rounding_fixes_sum():
    amounts = allocate_category_add(
        category_gap_amount=100.0,
        fund_gaps={"A": 1.0, "B": 1.0, "C": 1.0},
    )
    assert round(sum(amounts.values()), 2) == 100.0


def test_is_performance_blocked_add_reduce():
    assert is_performance_blocked_add({"signal_type": "reduce", "reasons": []}) is True


def test_is_performance_blocked_add_watch_with_rule():
    assert is_performance_blocked_add(
        {
            "signal_type": "watch",
            "reasons": [{"layer": "performance", "rule": "sharpe_1y", "detail": "x"}],
        }
    ) is True


def test_is_performance_blocked_add_hold():
    assert is_performance_blocked_add({"signal_type": "hold", "reasons": []}) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && pytest tests/test_intra_category.py -v`  
Expected: FAIL — `ModuleNotFoundError: intra_category`

- [ ] **Step 3: Implement `intra_category.py`**

```python
# backend/app/services/signals/intra_category.py
from __future__ import annotations

PERFORMANCE_BLOCK_RULES = frozenset(
    {"excess_return_1y", "peer_return_percentile_3m", "max_drawdown_1y", "sharpe_1y"}
)


def is_performance_blocked_add(perf_signal: dict | None) -> bool:
    if not perf_signal:
        return False
    if perf_signal.get("signal_type") == "reduce":
        return True
    if perf_signal.get("signal_type") != "watch":
        return False
    return any(
        reason.get("rule") in PERFORMANCE_BLOCK_RULES
        for reason in perf_signal.get("reasons") or []
        if reason.get("layer") == "performance"
    )


def resolve_intra_category_weights(
    mode: str,
    fund_categories: dict[str, str],
    market_value_by_code: dict[str, float],
    *,
    category: str,
    custom_weights: dict[str, float] | None,
) -> dict[str, float]:
    codes = [code for code, cat in fund_categories.items() if cat == category]
    if not codes:
        return {}

    if mode == "custom" and custom_weights:
        specified = {c: custom_weights[c] for c in codes if c in custom_weights}
        unspecified = [c for c in codes if c not in custom_weights]
        if not unspecified:
            total = sum(specified.values())
            return {c: v / total for c, v in specified.items()} if total else {}
        remaining = max(0.0, 1.0 - sum(specified.values()))
        share = remaining / len(unspecified) if unspecified else 0.0
        result = dict(specified)
        for code in unspecified:
            result[code] = share
        total = sum(result.values())
        return {c: v / total for c, v in result.items()} if total else {}

    if mode == "pro_rata":
        total_mv = sum(market_value_by_code.get(c, 0.0) for c in codes)
        if total_mv <= 0:
            n = len(codes)
            return {c: 1.0 / n for c in codes}
        return {c: market_value_by_code.get(c, 0.0) / total_mv for c in codes}

    n = len(codes)
    return {c: 1.0 / n for c in codes}


def compute_fund_gaps(
    *,
    market_value_by_code: dict[str, float],
    intra_weights: dict[str, float],
    total_value: float,
    category_target: float,
) -> dict[str, float]:
    gaps: dict[str, float] = {}
    for code, w in intra_weights.items():
        target_mv = category_target * w * total_value
        gap = target_mv - market_value_by_code.get(code, 0.0)
        gaps[code] = max(0.0, round(gap, 2))
    return gaps


def allocate_category_add(
    *,
    category_gap_amount: float,
    fund_gaps: dict[str, float],
) -> dict[str, float]:
    positive = {c: g for c, g in fund_gaps.items() if g > 0}
    total_gap = sum(positive.values())
    if total_gap <= 0 or category_gap_amount <= 0:
        return {c: 0.0 for c in fund_gaps}

    codes = sorted(positive.keys())
    amounts: dict[str, float] = {}
    allocated = 0.0
    for i, code in enumerate(codes):
        if i == len(codes) - 1:
            amounts[code] = round(category_gap_amount - allocated, 2)
        else:
            share = round(category_gap_amount * positive[code] / total_gap, 2)
            amounts[code] = share
            allocated += share
    for code in fund_gaps:
        amounts.setdefault(code, 0.0)
    return amounts
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && pytest tests/test_intra_category.py -v`  
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/signals/intra_category.py backend/tests/test_intra_category.py
git commit -m "feat(signals): add intra-category rebalance allocation helpers"
```

---

## Task 2: StrategyConfig 持久化

**Files:**
- Modify: `backend/app/db/models.py`
- Modify: `backend/app/db/session.py`
- Modify: `backend/app/schemas/settings.py`

- [ ] **Step 1: Add model fields**

在 `StrategyConfig` 增加：

```python
intra_category_mode: str = "equal"
fund_target_weights_json: str = "{}"
```

- [ ] **Step 2: SQLite migration**

在 `session.py` 增加 `_STRATEGY_CONFIG_COLUMNS` 与 `_ensure_strategy_config_columns()`，在 `create_db_and_tables()` 末尾调用：

```python
_STRATEGY_CONFIG_COLUMNS = (
    ("intra_category_mode", "TEXT NOT NULL DEFAULT 'equal'"),
    ("fund_target_weights_json", "TEXT NOT NULL DEFAULT '{}'"),
)
```

- [ ] **Step 3: Extend schemas**

```python
# settings.py
from typing import Literal

IntraCategoryMode = Literal["equal", "pro_rata", "custom"]

class StrategyOut(BaseModel):
    template_name: str
    target_weights: dict[str, float]
    thresholds: dict[str, float]
    intra_category_mode: str = "equal"
    fund_target_weights: dict[str, float] = Field(default_factory=dict)

class StrategyUpdateIn(BaseModel):
    template_name: str
    target_weights: dict[str, float] | None = None
    thresholds: StrategyThresholds | None = None
    intra_category_mode: IntraCategoryMode | None = None
    fund_target_weights: dict[str, float] | None = None
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/db/models.py backend/app/db/session.py backend/app/schemas/settings.py
git commit -m "feat(settings): persist intra-category mode and fund target weights"
```

---

## Task 3: Settings API 读写与校验

**Files:**
- Modify: `backend/app/api/routes/settings.py`
- Test: `backend/tests/test_api_settings.py`

- [ ] **Step 1: Write failing test**

```python
def test_put_strategy_intra_category_mode():
    resp = client.put(
        "/api/settings/strategy",
        json={"template_name": "balanced", "intra_category_mode": "pro_rata"},
    )
    assert resp.status_code == 200
    assert resp.json()["intra_category_mode"] == "pro_rata"


def test_put_strategy_custom_fund_weights_must_sum_to_one():
    resp = client.put(
        "/api/settings/strategy",
        json={
            "template_name": "balanced",
            "intra_category_mode": "custom",
            "fund_target_weights": {"110011": 0.6, "000001": 0.3},
        },
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run test — expect FAIL**

Run: `cd backend && pytest tests/test_api_settings.py::test_put_strategy_intra_category_mode -v`

- [ ] **Step 3: Update `_config_to_out` and `update_strategy`**

```python
def _config_to_out(config: StrategyConfig) -> StrategyOut:
    ...
    fund_targets = json.loads(config.fund_target_weights_json or "{}")
    return StrategyOut(
        ...
        intra_category_mode=config.intra_category_mode or "equal",
        fund_target_weights=fund_targets if isinstance(fund_targets, dict) else {},
    )

def _validate_fund_target_weights(weights: dict[str, float]) -> None:
    total = sum(weights.values())
    if not (0.99 <= total <= 1.01):
        raise HTTPException(
            status_code=422,
            detail=f"fund_target_weights must sum to 1.0, got {total:.4f}",
        )

# in update_strategy:
mode = payload.intra_category_mode or config.intra_category_mode or "equal"
if payload.intra_category_mode is not None:
    mode = payload.intra_category_mode
if mode == "custom":
    if not payload.fund_target_weights:
        raise HTTPException(status_code=422, detail="custom intra_category_mode requires fund_target_weights")
    _validate_fund_target_weights(payload.fund_target_weights)
    config.fund_target_weights_json = json.dumps(payload.fund_target_weights)
elif payload.fund_target_weights is not None:
    _validate_fund_target_weights(payload.fund_target_weights)
    config.fund_target_weights_json = json.dumps(payload.fund_target_weights)
config.intra_category_mode = mode
```

- [ ] **Step 4: Run settings tests**

Run: `cd backend && pytest tests/test_api_settings.py -v`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/settings.py backend/tests/test_api_settings.py
git commit -m "feat(api): expose intra-category strategy settings"
```

---

## Task 4: 接入 `aggregate_signals` 与 `run_signal_engine`

**Files:**
- Modify: `backend/app/services/signals/engine.py`
- Modify: `backend/tests/test_signals_engine.py`

- [ ] **Step 1: Write failing integration test**

```python
def test_aggregate_signals_allocates_by_intra_category_gap_not_equal_split():
    rebalance = [{
        "category": "stock",
        "signal_type": "add",
        "deviation_pct": 9.1,
        "suggested_amount": 3000.0,
        "detail": "股票型低配 9.1%，建议增配 ¥3000",
    }]
    fund_categories = {"A": "stock", "B": "stock", "C": "stock"}
    market_value_by_code = {"A": 500.0, "B": 2500.0, "C": 2500.0}
    total_value = 10000.0
    category_targets = {"stock": 0.4}

    results = aggregate_signals(
        rebalance, [], [],
        fund_categories,
        market_value_by_code=market_value_by_code,
        total_value=total_value,
        category_targets=category_targets,
        intra_category_mode="equal",
    )
    by_code = {r["fund_code"]: r for r in results if r["fund_code"]}
    amounts = [by_code[c]["suggested_amount"] for c in ("A", "B", "C")]
    assert amounts[0] > amounts[1]  # A 远低于等权目标，应分到更多
    assert abs(sum(amounts) - 3000.0) < 0.05


def test_aggregate_signals_performance_blocked_gets_zero_amount():
    rebalance = [{
        "category": "stock",
        "signal_type": "add",
        "deviation_pct": 10.0,
        "suggested_amount": 1000.0,
        "detail": "股票型低配",
    }]
    performance = [{
        "fund_code": "A",
        "signal_type": "reduce",
        "reasons": [{"layer": "performance", "rule": "excess_return_1y", "detail": "差"}],
        "detail": "差",
    }]
    results = aggregate_signals(
        rebalance, [], performance,
        {"A": "stock", "B": "stock"},
        market_value_by_code={"A": 100.0, "B": 4900.0},
        total_value=10000.0,
        category_targets={"stock": 0.5},
        intra_category_mode="equal",
    )
    by_code = {r["fund_code"]: r for r in results if r["fund_code"]}
    assert by_code["A"]["suggested_amount"] == 0.0
    assert by_code["B"]["suggested_amount"] > 0
```

- [ ] **Step 2: Run — expect FAIL**

Run: `cd backend && pytest tests/test_signals_engine.py::test_aggregate_signals_allocates_by_intra_category_gap_not_equal_split -v`

- [ ] **Step 3: Refactor `aggregate_signals`**

要点：

1. 扩展函数签名（keyword-only 新参数）。
2. 在循环前，按 `rebalance` 中 `signal_type=="add"` 的类别预计算 `add_amounts_by_code`：

```python
def _build_category_add_amounts(
    rebalance, fund_categories, market_value_by_code, total_value,
    category_targets, intra_category_mode, fund_target_weights, perf_by_fund,
) -> dict[str, float]:
    amounts: dict[str, float] = {}
    for signal in rebalance:
        if signal["signal_type"] != "add":
            continue
        category = signal["category"]
        gap_amount = abs(signal["suggested_amount"])
        T_C = category_targets.get(category, 0.0)
        intra_w = resolve_intra_category_weights(
            intra_category_mode, fund_categories, market_value_by_code,
            category=category, custom_weights=fund_target_weights,
        )
        fund_gaps = compute_fund_gaps(
            market_value_by_code=market_value_by_code,
            intra_weights=intra_w,
            total_value=total_value,
            category_target=T_C,
        )
        for code in intra_w:
            if is_performance_blocked_add(perf_by_fund.get(code)):
                fund_gaps[code] = 0.0
        allocated = allocate_category_add(
            category_gap_amount=gap_amount,
            fund_gaps=fund_gaps,
        )
        for code, value in allocated.items():
            amounts[code] = amounts.get(code, 0.0) + value
    return amounts
```

3. 单只基金循环内替换均摊：

```python
# 删除:
#   suggested_amount += abs(rebalance_signal["suggested_amount"]) / share
# 改为:
add_amounts = _build_category_add_amounts(...)
...
if rebalance_signal and rebalance_signal["signal_type"] == "add":
    suggested_amount += add_amounts.get(fund_code, 0.0)
```

4. 更新 rebalance reason `detail`，追加类内信息（从 `fund_gaps` / 分配额读取）。

5. 业绩 blocked 时 append reason：

```python
{"layer": "performance", "rule": "performance_blocked_add", "detail": "业绩偏弱，不参与增配分配"}
```

6. `_load_strategy` 返回 `(target, thresholds, mode, fund_target_weights)`；`run_signal_engine` 构建 `market_value_by_code` 并传入 `aggregate_signals`。

- [ ] **Step 4: 更新 `test_aggregate_signals_weak_rebalance_add_classified_as_add`**

改为传入 `market_value_by_code` / `total_value` / `category_targets`，断言 `sum(suggested_amount) ≈ 52806` 且三只金额 **不全相等**。

- [ ] **Step 5: Run signal engine tests**

Run: `cd backend && pytest tests/test_signals_engine.py tests/test_intra_category.py -v`  
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/signals/engine.py backend/tests/test_signals_engine.py
git commit -m "feat(signals): allocate category add by intra-category weight gaps"
```

---

## Task 5: Settings 前端（最小 UI）

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/SettingsPage.tsx`

- [ ] **Step 1: Extend types**

```typescript
export interface StrategyConfig {
  template_name: string
  target_weights: Record<string, number>
  thresholds: { ... }
  intra_category_mode: 'equal' | 'pro_rata' | 'custom'
  fund_target_weights: Record<string, number>
}
```

- [ ] **Step 2: Settings 增加下拉（仅 equal / pro_rata）**

在策略配置区块增加：

```tsx
const INTRA_CATEGORY_OPTIONS = [
  { value: 'equal', label: '类内等权目标' },
  { value: 'pro_rata', label: '按现占比维持结构' },
] as const
```

保存时 `updateStrategy({ ..., intra_category_mode: intraCategoryMode })`。

- [ ] **Step 3: Build 验证**

Run: `cd frontend && npm run build`  
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts frontend/src/pages/SettingsPage.tsx
git commit -m "feat(settings): add intra-category allocation mode selector"
```

---

## Task 6: 文档与 README 收尾

**Files:**
- Modify: `docs/superpowers/specs/active/2026-06-21-fund-quant-assistant-design.md`
- Modify: `docs/superpowers/specs/active/2026-06-22-intra-category-rebalance-allocation-design.md`
- Modify: `docs/superpowers/README.md`
- Move: `docs/superpowers/plans/active/2026-06-22-intra-category-rebalance-allocation.md` → `plans/completed/`

- [ ] **Step 1: 主 spec §3 suggested_amount 改为 v1.3 正式行为（删除「临时均摊」）**
- [ ] **Step 2: v1.3 spec Changelog 增加「已交付」**
- [ ] **Step 3: README plan 列指向 completed**
- [ ] **Step 4: Plan Status → completed，全部 checkbox `[x]`**

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/
git commit -m "docs: mark v1.3 intra-category allocation as delivered"
```

---

## Task 7: 全量验收

- [ ] **Step 1: Backend 全量测试**

Run: `cd backend && pytest tests -v`  
Expected: ALL PASS

- [ ] **Step 2: Frontend build**

Run: `cd frontend && npm run build`  
Expected: PASS

- [ ] **Step 3: 手动冒烟**

1. Settings 切换「类内等权 / 按现占比」→ 保存  
2. 触发 sync / 信号引擎  
3. 信号页增配 tab：确认不同基金 **建议金额不再全部相同**  
4. 业绩差基金金额为 0（若持仓存在 reduce 信号）

---

## Spec 覆盖自检

| Spec 需求 | Task |
|-----------|------|
| 类内目标权重 equal/pro_rata/custom | 1, 2, 3 |
| 缺口比例分配 + 四舍五入修正 | 1, 4 |
| 业绩过滤 | 1, 4 |
| aggregate_signals 重构 | 4 |
| 原因文案区分大类/类内 | 4 |
| Settings API | 2, 3, 5 |
| 限购在分配之后 | 4（现有 `apply_purchase_limits` 顺序不变） |
| 测试用例表 | 1, 4, 7 |
| 主 spec 文档更新 | 6 |

---

## 执行顺序

Task 1 → 2 → 3 → 4 → 5 → 6 → 7。Task 4 依赖 1–3；Task 5 可与 Task 4 并行。
