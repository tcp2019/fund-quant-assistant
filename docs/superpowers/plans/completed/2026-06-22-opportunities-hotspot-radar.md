# v1.4 机会中心 + 热点雷达 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** completed
> **Created:** 2026-06-22
> **Spec:** docs/superpowers/specs/active/2026-06-22-opportunities-hotspot-radar-design.md
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Based on:** docs/superpowers/plans/completed/2026-06-22-intra-category-rebalance-allocation.md

**Goal:** 聚合量化信号与主题业绩排行，在 Dashboard 与 `/opportunities` 提供「该卖 / 该买 / 可探索」行动清单和热点主题雷达。

**Architecture:** 新增 `action_classifier`（与前端 `signalActionType` 对齐）、`theme_heat`（主题近1月中位数）、`opportunities` 聚合服务；暴露 `GET /api/opportunities`；前端 Dashboard 摘要 + 机会详情页。

**Tech Stack:** Python 3.11, FastAPI, SQLModel, pytest | React 18, TypeScript, Tailwind

---

## 文件结构

```
backend/
├── app/schemas/opportunities.py              # ActionItemOut, HotThemeOut, OpportunitiesOut
├── app/services/signals/action_classifier.py # 信号行动分类
├── app/services/theme_heat.py                # 主题热点评分
├── app/services/opportunities.py             # 聚合 build_opportunities
├── app/api/routes/opportunities.py           # GET /api/opportunities
├── app/main.py                               # register router
├── tests/test_action_classifier.py
├── tests/test_theme_heat.py
├── tests/test_opportunities.py
└── tests/test_api_opportunities.py

frontend/
├── src/types/index.ts                        # Opportunities 类型
├── src/api/client.ts                         # fetchOpportunities
├── src/components/ActionSummaryCards.tsx
├── src/components/HotThemeRadar.tsx
├── src/components/ActionList.tsx
├── src/pages/OpportunitiesPage.tsx
├── src/pages/Dashboard.tsx                   # 嵌入摘要 + 雷达
├── src/components/Layout.tsx                 # 导航「机会」
└── src/App.tsx                               # 路由 /opportunities
```

---

## Task 1: `action_classifier.py`（TDD）

**Files:**
- Create: `backend/app/services/signals/action_classifier.py`
- Create: `backend/tests/test_action_classifier.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_action_classifier.py
from app.services.signals.action_classifier import classify_signal_action


def test_reduce_is_sell():
    assert classify_signal_action("reduce", [], -5000.0, -30.0) == "reduce"


def test_purchase_limit_maps_to_watch():
    reasons = [{"layer": "purchase_limit", "rule": "purchase_limit_blocked", "detail": "x"}]
    assert classify_signal_action("add", reasons, 1000.0, 20.0) == "watch"


def test_hold_with_rebalance_add_maps_to_add():
    reasons = [
        {"layer": "rebalance", "rule": "category_underweight", "detail": "低配"},
        {"layer": "rebalance", "rule": "add", "detail": "增配"},
    ]
    assert classify_signal_action("hold", reasons, 500.0, 18.0) == "add"


def test_hold_reduce_maps_to_reduce():
    reasons = [
        {"layer": "rebalance", "rule": "category_overweight", "detail": "超配"},
        {"layer": "rebalance", "rule": "reduce", "detail": "减配"},
    ]
    assert classify_signal_action("hold", reasons, -800.0, -22.0) == "reduce"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_action_classifier.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/signals/action_classifier.py
"""Classify raw signal records into actionable types (mirrors frontend signalActionType)."""

from __future__ import annotations

PURCHASE_LIMIT_WATCH_RULES = frozenset(
    {"redemption_hard_to_rebuy", "purchase_limit_blocked", "purchase_suspended"}
)
PURCHASE_LIMIT_ADD_BLOCK_RULES = frozenset({"purchase_limit_blocked", "purchase_suspended"})


def _protected_by_purchase_limit(reasons: list[dict]) -> bool:
    return any(
        reason.get("layer") == "purchase_limit"
        and reason.get("rule") in PURCHASE_LIMIT_WATCH_RULES
        for reason in reasons
    )


def _rebalance_rules(reasons: list[dict]) -> set[str]:
    return {
        reason.get("rule", "")
        for reason in reasons
        if reason.get("layer") == "rebalance"
    }


def classify_signal_action(
    signal_type: str,
    reasons: list[dict],
    suggested_amount: float,
    score: float,
) -> str:
    if _protected_by_purchase_limit(reasons):
        return "watch"

    if signal_type != "hold":
        return signal_type

    rebalance = _rebalance_rules(reasons)
    if (
        suggested_amount > 0
        and score > 0
        and rebalance & {"add", "category_underweight"}
    ):
        blocked = any(
            reason.get("layer") == "purchase_limit"
            and reason.get("rule") in PURCHASE_LIMIT_ADD_BLOCK_RULES
            for reason in reasons
        )
        return "watch" if blocked else "add"

    if (
        suggested_amount < 0
        and score < 0
        and rebalance & {"reduce", "category_overweight"}
    ):
        return "reduce"

    return signal_type
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_action_classifier.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/signals/action_classifier.py backend/tests/test_action_classifier.py
git commit -m "feat: add signal action classifier for opportunities"
```

---

## Task 2: `theme_heat.py`（TDD）

**Files:**
- Create: `backend/app/services/theme_heat.py`
- Create: `backend/tests/test_theme_heat.py`

- [ ] **Step 1: Write failing tests**

```python
# backend/tests/test_theme_heat.py
from statistics import median

from sqlmodel import Session

from app.db.session import engine
from app.services.fund_catalog import load_catalog_fixture
from app.services.fund_rankings import load_rank_fixture
from app.services.theme_heat import THEME_TO_CATEGORY, compute_theme_heat, rank_hot_themes


def test_theme_to_category_mapping():
    assert THEME_TO_CATEGORY["cpo_optics"] == "stock"
    assert THEME_TO_CATEGORY["qdii"] == "qdii"


def test_compute_theme_heat_cpo():
    with Session(engine) as session:
        load_catalog_fixture(session)
        load_rank_fixture(session, "all_open", "fund_open_fund_rank_em_sample.json")
        heat = compute_theme_heat(session, "cpo_optics")
    assert heat is not None
    assert heat.return_1m_median == 12.5
    assert heat.heat_score == 12.5


def test_rank_hot_themes_sorted():
    with Session(engine) as session:
        load_catalog_fixture(session)
        load_rank_fixture(session, "all_open", "fund_open_fund_rank_em_sample.json")
        ranked = rank_hot_themes(session, limit=3)
    assert len(ranked) >= 1
    scores = [row.heat_score for row in ranked]
    assert scores == sorted(scores, reverse=True)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_theme_heat.py -v`
Expected: FAIL

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/theme_heat.py
from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from sqlmodel import Session

from app.services.fund_rankings import fetch_all_open_rankings, filter_rankings_for_theme
from app.services.fund_themes import THEME_LABELS

THEME_TO_CATEGORY: dict[str, str] = {
    "storage_semiconductor": "stock",
    "cpo_optics": "stock",
    "ai_compute": "stock",
    "new_energy": "stock",
    "healthcare": "stock",
    "consumer": "stock",
    "dividend": "stock",
    "gold": "gold",
    "qdii": "qdii",
}

MIN_THEME_SAMPLE = 3
HEAT_SAMPLE_LIMIT = 20


@dataclass(frozen=True)
class ThemeHeatRow:
    theme: str
    label: str
    heat_score: float
    return_1m_median: float


def compute_theme_heat(session: Session, theme_id: str) -> ThemeHeatRow | None:
    if theme_id not in THEME_LABELS:
        return None
    try:
        rows, _source = fetch_all_open_rankings(session)
    except Exception:
        return None

    picked = filter_rankings_for_theme(
        session,
        theme_id,
        rows,
        exclude_codes=set(),
        limit=HEAT_SAMPLE_LIMIT,
        sort_by="return_1m",
    )
    returns = [row["return_1m"] for row in picked if row.get("return_1m") is not None]
    if len(returns) < MIN_THEME_SAMPLE:
        return None

    med = float(median(returns))
    return ThemeHeatRow(
        theme=theme_id,
        label=THEME_LABELS[theme_id],
        heat_score=med,
        return_1m_median=med,
    )


def rank_hot_themes(session: Session, limit: int = 9) -> list[ThemeHeatRow]:
    rows: list[ThemeHeatRow] = []
    for theme_id in THEME_LABELS:
        heat = compute_theme_heat(session, theme_id)
        if heat is not None:
            rows.append(heat)
    rows.sort(key=lambda item: item.heat_score, reverse=True)
    return rows[:limit]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_theme_heat.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/theme_heat.py backend/tests/test_theme_heat.py
git commit -m "feat: add theme heat scoring from akshare rankings"
```

---

## Task 3: Schemas + `opportunities.py` 聚合服务（TDD）

**Files:**
- Create: `backend/app/schemas/opportunities.py`
- Create: `backend/app/services/opportunities.py`
- Create: `backend/tests/test_opportunities.py`

- [ ] **Step 1: Write schemas**

```python
# backend/app/schemas/opportunities.py
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.funds import FundCandidateOut


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

- [ ] **Step 2: Write failing service tests**

```python
# backend/tests/test_opportunities.py
import json

from sqlmodel import Session

from app.db.models import Holding, SignalRecord, Snapshot
from app.db.session import engine
from app.services.fund_catalog import load_catalog_fixture
from app.services.fund_rankings import load_rank_fixture
from app.services.opportunities import build_opportunities, summarize_reason


def test_summarize_reason():
    reasons = [{"layer": "rebalance", "rule": "category_underweight", "detail": "股票型低配"}]
    assert "大类低配" in summarize_reason(reasons) or "category_underweight" in summarize_reason(reasons)


def test_build_opportunities_partitions_actions():
    with Session(engine) as session:
        snap = Snapshot(source="test")
        session.add(snap)
        session.commit()
        session.refresh(snap)

        session.add(
            Holding(
                snapshot_id=snap.id,
                fund_code="110011",
                fund_name="测试基金A",
                shares=100,
                cost=1000,
                market_value=5000,
            )
        )
        session.add(
            SignalRecord(
                snapshot_id=snap.id,
                fund_code="110011",
                signal_type="reduce",
                score=-25.0,
                strength=4,
                suggested_amount=-3000.0,
                reasons_json=json.dumps(
                    [{"layer": "rebalance", "rule": "reduce", "detail": "集中度偏高"}]
                ),
            )
        )
        session.add(
            SignalRecord(
                snapshot_id=snap.id,
                fund_code="",
                signal_type="add",
                score=30.0,
                strength=4,
                suggested_amount=10000.0,
                reasons_json=json.dumps(
                    [
                        {
                            "layer": "rebalance",
                            "rule": "category_underweight",
                            "detail": "股票型低配",
                            "category": "stock",
                            "category_label": "股票型",
                        }
                    ]
                ),
            )
        )
        session.commit()

        load_catalog_fixture(session)
        load_rank_fixture(session, "all_open", "fund_open_fund_rank_em_sample.json")

        out = build_opportunities(session, sell_limit=5, buy_limit=5, explore_limit=5, theme_limit=3)
        assert out.snapshot_id == snap.id
        assert len(out.sell_actions) == 1
        assert out.sell_actions[0].action == "sell"
        assert out.sell_actions[0].fund_code == "110011"
        assert len(out.explore_actions) >= 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && pytest tests/test_opportunities.py -v`
Expected: FAIL

- [ ] **Step 4: Write opportunities service**

```python
# backend/app/services/opportunities.py
from __future__ import annotations

import json

from sqlmodel import Session, select

from app.db.models import Holding, SignalRecord
from app.repositories.portfolio import get_latest_snapshot, get_overview
from app.schemas.funds import FundCandidateOut
from app.schemas.opportunities import ActionItemOut, HotThemeOut, OpportunitiesOut
from app.services.fund_recommendations import recommend_funds, recommend_funds_by_theme
from app.services.signals.action_classifier import classify_signal_action
from app.services.theme_heat import THEME_TO_CATEGORY, rank_hot_themes

REASON_RULE_LABELS: dict[str, str] = {
    "add": "增配",
    "reduce": "减配",
    "category_underweight": "大类低配",
    "category_overweight": "大类超配",
    "single_fund_concentration": "集中度",
    "performance_blocked_add": "业绩过滤",
    "purchase_limit_blocked": "限购受阻",
    "purchase_suspended": "暂停申购",
    "redemption_hard_to_rebuy": "卖出难买回",
}


def _parse_reasons(raw: str) -> list[dict]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def summarize_reason(reasons: list[dict], max_length: int = 80) -> str:
    if not reasons:
        return "—"
    first = reasons[0]
    rule = first.get("rule", "")
    label = REASON_RULE_LABELS.get(rule, rule)
    detail = first.get("detail", "")
    text = f"{label} · {detail}" if detail else label
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}…"


def _extract_category(reasons: list[dict]) -> tuple[str | None, str | None]:
    for reason in reasons:
        category = reason.get("category")
        if category:
            return category, reason.get("category_label")
    return None, None


def _underweight_categories(records: list[SignalRecord]) -> dict[str, str]:
    result: dict[str, str] = {}
    for record in records:
        reasons = _parse_reasons(record.reasons_json)
        for reason in reasons:
            if reason.get("rule") == "category_underweight" and reason.get("category"):
                result[reason["category"]] = reason.get("category_label") or reason["category"]
    return result


def build_opportunities(
    session: Session,
    *,
    sell_limit: int = 5,
    buy_limit: int = 5,
    explore_limit: int = 5,
    theme_limit: int = 5,
) -> OpportunitiesOut:
    snap = get_latest_snapshot(session)
    if snap is None:
        return OpportunitiesOut(
            snapshot_id=None,
            sell_actions=[],
            buy_actions=[],
            explore_actions=[],
            hot_themes=[],
        )

    records = session.exec(
        select(SignalRecord)
        .where(SignalRecord.snapshot_id == snap.id)
        .order_by(SignalRecord.score.desc())
    ).all()
    holdings = session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
    name_by_code = {h.fund_code: h.fund_name for h in holdings}
    held_codes = {h.fund_code for h in holdings if h.fund_code}
    underweight = _underweight_categories(records)

    overview = get_overview(session, snap.id)
    theme_weight = {
        item.theme: item.weight_pct for item in (overview.theme_allocation or [])
    }

    sell_actions: list[ActionItemOut] = []
    buy_actions: list[ActionItemOut] = []
    explore_actions: list[ActionItemOut] = []

    for record in records:
        reasons = _parse_reasons(record.reasons_json)
        action_type = classify_signal_action(
            record.signal_type, reasons, record.suggested_amount, record.score
        )
        category, category_label = _extract_category(reasons)

        if action_type == "reduce" and record.suggested_amount < 0 and record.fund_code:
            sell_actions.append(
                ActionItemOut(
                    action="sell",
                    fund_code=record.fund_code,
                    fund_name=name_by_code.get(record.fund_code),
                    category=category,
                    category_label=category_label,
                    suggested_amount=record.suggested_amount,
                    score=record.score,
                    strength=record.strength,
                    reason_summary=summarize_reason(reasons),
                    signal_id=record.id,
                )
            )
        elif action_type == "add" and record.suggested_amount > 0 and record.fund_code:
            buy_actions.append(
                ActionItemOut(
                    action="add_holding",
                    fund_code=record.fund_code,
                    fund_name=name_by_code.get(record.fund_code),
                    category=category,
                    category_label=category_label,
                    suggested_amount=record.suggested_amount,
                    score=record.score,
                    strength=record.strength,
                    reason_summary=summarize_reason(reasons),
                    signal_id=record.id,
                )
            )
        elif (
            action_type == "add"
            and record.suggested_amount > 0
            and not record.fund_code
            and category
        ):
            candidates = recommend_funds(session, category, held_codes, limit=3)
            explore_actions.append(
                ActionItemOut(
                    action="explore",
                    fund_code="",
                    fund_name=None,
                    category=category,
                    category_label=category_label,
                    suggested_amount=record.suggested_amount,
                    score=record.score,
                    strength=record.strength,
                    reason_summary=summarize_reason(reasons),
                    signal_id=record.id,
                    candidates=candidates,
                )
            )

    sell_actions.sort(key=lambda item: (abs(item.suggested_amount), abs(item.score)), reverse=True)
    buy_actions.sort(key=lambda item: item.suggested_amount, reverse=True)
    explore_actions.sort(key=lambda item: abs(item.suggested_amount), reverse=True)

    hot_rows = rank_hot_themes(session, limit=theme_limit)
    hot_themes: list[HotThemeOut] = []
    for row in hot_rows:
        mapped_category = THEME_TO_CATEGORY.get(row.theme, "stock")
        aligned = mapped_category in underweight
        candidates = recommend_funds_by_theme(session, row.theme, held_codes, limit=3)
        hot_themes.append(
            HotThemeOut(
                theme=row.theme,
                label=row.label,
                heat_score=row.heat_score,
                return_1m_median=row.return_1m_median,
                portfolio_weight_pct=theme_weight.get(row.theme, 0.0),
                aligned_gap=aligned,
                aligned_category_label=underweight.get(mapped_category) if aligned else None,
                candidates=candidates,
            )
        )

    return OpportunitiesOut(
        snapshot_id=snap.id,
        data_as_of_date=overview.data_as_of_date,
        sell_actions=sell_actions[:sell_limit],
        buy_actions=buy_actions[:buy_limit],
        explore_actions=explore_actions[:explore_limit],
        hot_themes=hot_themes,
    )
```

- [ ] **Step 5: Fix imports if `get_overview` signature differs**

Check `backend/app/repositories/portfolio.py` — use existing `build_portfolio_overview` or equivalent. Adjust import to match actual function name.

- [ ] **Step 6: Run tests**

Run: `cd backend && pytest tests/test_opportunities.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/opportunities.py backend/app/services/opportunities.py backend/tests/test_opportunities.py
git commit -m "feat: aggregate opportunities from signals and theme heat"
```

---

## Task 4: API 路由（TDD）

**Files:**
- Create: `backend/app/api/routes/opportunities.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_api_opportunities.py`

- [ ] **Step 1: Write failing API test**

```python
# backend/tests/test_api_opportunities.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_opportunities_empty_snapshot():
    resp = client.get("/api/opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["snapshot_id"] is None
    assert data["sell_actions"] == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_api_opportunities.py -v`
Expected: FAIL — 404

- [ ] **Step 3: Add route + register**

```python
# backend/app/api/routes/opportunities.py
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.deps import get_db
from app.schemas.opportunities import OpportunitiesOut
from app.services.opportunities import build_opportunities

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


@router.get("", response_model=OpportunitiesOut)
def list_opportunities(
    sell_limit: int = Query(default=5, ge=1, le=20),
    buy_limit: int = Query(default=5, ge=1, le=20),
    explore_limit: int = Query(default=5, ge=1, le=20),
    theme_limit: int = Query(default=5, ge=1, le=20),
    session: Session = Depends(get_db),
):
    return build_opportunities(
        session,
        sell_limit=sell_limit,
        buy_limit=buy_limit,
        explore_limit=explore_limit,
        theme_limit=theme_limit,
    )
```

```python
# backend/app/main.py — add import and include_router
from app.api.routes.opportunities import router as opportunities_router
# ...
app.include_router(opportunities_router)
```

- [ ] **Step 4: Run tests**

Run: `cd backend && pytest tests/test_api_opportunities.py tests/test_opportunities.py tests/test_action_classifier.py tests/test_theme_heat.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/opportunities.py backend/app/main.py backend/tests/test_api_opportunities.py
git commit -m "feat: expose GET /api/opportunities"
```

---

## Task 5: 前端类型与 API client

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add TypeScript types**

```typescript
// frontend/src/types/index.ts — append
export interface ActionItem {
  action: 'sell' | 'add_holding' | 'explore'
  fund_code: string
  fund_name: string | null
  category: string | null
  category_label: string | null
  suggested_amount: number
  score: number
  strength: number
  reason_summary: string
  signal_id: number | null
  candidates: FundCandidate[]
}

export interface HotTheme {
  theme: string
  label: string
  heat_score: number
  return_1m_median: number | null
  portfolio_weight_pct: number
  aligned_gap: boolean
  aligned_category_label: string | null
  candidates: FundCandidate[]
}

export interface OpportunitiesOut {
  snapshot_id: number | null
  data_as_of_date: string | null
  sell_actions: ActionItem[]
  buy_actions: ActionItem[]
  explore_actions: ActionItem[]
  hot_themes: HotTheme[]
}
```

- [ ] **Step 2: Add fetch helper**

```typescript
// frontend/src/api/client.ts
export async function fetchOpportunities(params?: {
  sell_limit?: number
  buy_limit?: number
  explore_limit?: number
  theme_limit?: number
}): Promise<OpportunitiesOut> {
  const search = new URLSearchParams()
  if (params?.sell_limit) search.set('sell_limit', String(params.sell_limit))
  if (params?.buy_limit) search.set('buy_limit', String(params.buy_limit))
  if (params?.explore_limit) search.set('explore_limit', String(params.explore_limit))
  if (params?.theme_limit) search.set('theme_limit', String(params.theme_limit))
  const qs = search.toString()
  return api.get<OpportunitiesOut>(`/api/opportunities${qs ? `?${qs}` : ''}`)
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/api/client.ts
git commit -m "feat: add opportunities API types and client"
```

---

## Task 6: `ActionList` + `ActionSummaryCards` 组件

**Files:**
- Create: `frontend/src/components/ActionList.tsx`
- Create: `frontend/src/components/ActionSummaryCards.tsx`

- [ ] **Step 1: Create ActionList**

Reusable grouped list with expand for `reason_summary` + `candidates`. Reuse `formatSignalAmount`, `formatSignalScore`, `scoreTextClass` from `signalDisplay.ts`. Props:

```typescript
interface ActionListProps {
  title: string
  items: ActionItem[]
  emptyText: string
  tone: 'sell' | 'buy' | 'explore'
}
```

- [ ] **Step 2: Create ActionSummaryCards**

Three cards (sell / add_holding / explore) showing first 3 items each from `OpportunitiesOut`. Footer link: `Link to="/opportunities?tab=actions"`. Empty card text per spec.

- [ ] **Step 3: Manual smoke**

Run frontend dev server; temporarily render cards with mock data if API not wired yet.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ActionList.tsx frontend/src/components/ActionSummaryCards.tsx
git commit -m "feat: add action summary cards and action list components"
```

---

## Task 7: `HotThemeRadar` 组件

**Files:**
- Create: `frontend/src/components/HotThemeRadar.tsx`

- [ ] **Step 1: Implement horizontal scroll strip**

Each chip shows: `label`, `近1月 {return_1m_median}%`, `组合 {portfolio_weight_pct}%`. If `aligned_gap`, badge「与{aligned_category_label}低配一致」. Link to `/opportunities?tab=themes`.

- [ ] **Step 2: Empty state**

`hot_themes.length === 0` → 「热点数据暂不可用，请稍后同步」

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/HotThemeRadar.tsx
git commit -m "feat: add hot theme radar component"
```

---

## Task 8: `OpportunitiesPage` + 路由 + 导航

**Files:**
- Create: `frontend/src/pages/OpportunitiesPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: OpportunitiesPage**

- Read `?tab=actions|themes` from URL (`useSearchParams`)
- Fetch `fetchOpportunities({ sell_limit: 10, buy_limit: 10, explore_limit: 10, theme_limit: 9 })`
- Tab「行动清单」: three `ActionList` sections
- Tab「热点雷达」: grid of theme cards with candidates (reuse candidate row UI from `ThemeExposurePanel`)
- Disclaimer banner (amber) matching SignalsPage

- [ ] **Step 2: Register route and nav**

```typescript
// App.tsx
import OpportunitiesPage from './pages/OpportunitiesPage'
// <Route path="opportunities" element={<OpportunitiesPage />} />

// Layout.tsx — insert after 总览
{ to: '/opportunities', label: '机会' },
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/OpportunitiesPage.tsx frontend/src/App.tsx frontend/src/components/Layout.tsx
git commit -m "feat: add opportunities page and navigation"
```

---

## Task 9: Dashboard 集成

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Fetch opportunities on load**

Parallel with overview: `fetchOpportunities({ sell_limit: 3, buy_limit: 3, explore_limit: 3, theme_limit: 5 })`

- [ ] **Step 2: Render above existing stats**

```tsx
<ActionSummaryCards data={opportunities} />
<HotThemeRadar themes={opportunities.hot_themes} />
```

Only when `overview.holdings.length > 0`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: show action summary and hot themes on dashboard"
```

---

## Task 10: 全量验证与文档收尾

**Files:**
- Modify: `docs/superpowers/README.md` — plan active → completed（实现完成后）
- Modify: `docs/superpowers/plans/active/2026-06-22-opportunities-hotspot-radar.md` — Status: completed

- [ ] **Step 1: Run backend tests**

Run: `cd backend && pytest -q`
Expected: all pass

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: build succeeds

- [ ] **Step 3: Manual acceptance**

1. Dashboard 顶部见 3 类行动摘要 + 热点条
2. `/opportunities` 完整清单可展开候选
3. 热点主题显示近1月中位数与组合占比
4. 股票型低配时 semiconductor/CPO 等主题 `aligned_gap` 徽章可见

- [ ] **Step 4: Move plan to completed**

```bash
mv docs/superpowers/plans/active/2026-06-22-opportunities-hotspot-radar.md \
   docs/superpowers/plans/completed/2026-06-22-opportunities-hotspot-radar.md
```

Update plan header `Status: completed` and README plan column.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/
git commit -m "docs: mark v1.4 opportunities plan completed"
```

---

## Spec 覆盖自检

| Spec 要求 | 对应 Task |
|-----------|-----------|
| GET /api/opportunities | Task 3–4 |
| action_classifier | Task 1 |
| theme_heat 中位数 | Task 2 |
| sell / add_holding / explore 规则 | Task 1, 3 |
| Dashboard 摘要 Top 3 | Task 6, 9 |
| HotThemeRadar Top 5 | Task 7, 9 |
| /opportunities 双 Tab | Task 8 |
| aligned_gap | Task 2, 3 |
| candidates + data_source | Task 3（复用 recommend_*） |
| 空态 / 错误处理 | Task 6–9 |
| 合规文案 | Task 8 |
| 测试 | Task 1–4, 10 |

**v1.5 预留（本 plan 不实现）：** `news_headlines` 字段、新闻 API
