# v1.9 风格因子+宏观感知+模拟调仓 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development

> **Status:** completed
> **Created:** 2026-06-27
> **Spec:** docs/superpowers/specs/active/2026-06-27-factor-macro-whatif-design.md
> **Based on:** none

**Goal:** 风格暴露分析、宏观环境感知、模拟调仓what-if

**Architecture:** 子系统A新增factor_style.py+API；子系统B新增macro.py+API；子系统C前端WhatIfPanel纯计算组件

**Tech Stack:** Python/FastAPI/SQLModel/numpy, React 19/TypeScript/TanStack Query

---

### Task 1: 风格因子分类

**Files:**
- Create: `backend/tests/test_factor_style.py`
- Create: `backend/app/services/factor_style.py`

`backend/tests/test_factor_style.py`:
```python
from app.services.factor_style import classify_fund_style


def test_large_cap_value():
    r = classify_fund_style("易方达沪深300价值ETF联接", "stock")
    assert r["size"] == "large_cap"
    assert r["style"] == "value"


def test_small_cap_growth():
    r = classify_fund_style("天弘创业板成长ETF联接", "stock")
    assert r["size"] == "small_cap"
    assert r["style"] == "growth"


def test_balanced():
    r = classify_fund_style("兴全合润混合", "stock")
    assert r["size"] == "balanced"
    assert r["style"] == "balanced"


def test_bond_fund():
    r = classify_fund_style("易方达纯债债券", "bond")
    assert r["size"] == "balanced"
    assert r["style"] == "balanced"
```

`backend/app/services/factor_style.py`:
```python
"""Style factor classification for Chinese mutual funds."""

SIZE_LARGE_KEYWORDS = {"大盘", "蓝筹", "沪深300", "上证50", "中证100", "A50", "龙头"}
SIZE_SMALL_KEYWORDS = {"中小盘", "创业板", "科创板", "中证500", "中证1000", "国证2000", "小盘"}

STYLE_VALUE_KEYWORDS = {"价值", "红利", "低波", "高股息", "股息"}
STYLE_GROWTH_KEYWORDS = {"成长", "创新", "科技", "新兴", "未来", "新经济"}


def classify_fund_style(name: str, fund_type: str = "stock") -> dict:
    """Classify a fund into size and style categories based on name keywords."""
    # Non-stock funds don't get style classification
    if fund_type not in ("stock", "mixed", "qdii", ""):
        return {"size": "balanced", "style": "balanced"}

    size = "balanced"
    for kw in SIZE_LARGE_KEYWORDS:
        if kw in name:
            size = "large_cap"
            break
    if size == "balanced":
        for kw in SIZE_SMALL_KEYWORDS:
            if kw in name:
                size = "small_cap"
                break

    style = "balanced"
    for kw in STYLE_VALUE_KEYWORDS:
        if kw in name:
            style = "value"
            break
    if style == "balanced":
        for kw in STYLE_GROWTH_KEYWORDS:
            if kw in name:
                style = "growth"
                break

    return {"size": size, "style": style}


def compute_portfolio_style(session) -> dict:
    """Compute aggregate style exposure for current portfolio."""
    from collections import Counter
    from app.db.models import Holding
    from app.repositories.portfolio import get_latest_snapshot
    from sqlmodel import select

    snap = get_latest_snapshot(session)
    if not snap:
        return {"size_exposure": {}, "style_exposure": {}, "snapshot_id": None}

    holdings = session.exec(
        select(Holding).where(Holding.snapshot_id == snap.id)
    ).all()

    if not holdings:
        return {"size_exposure": {}, "style_exposure": {}, "snapshot_id": snap.id}

    total_value = sum(h.market_value for h in holdings)
    size_weight: Counter = Counter()
    style_weight: Counter = Counter()

    for h in holdings:
        style = classify_fund_style(h.fund_name, "stock")
        weight_pct = h.market_value / total_value * 100 if total_value else 0
        size_weight[style["size"]] += weight_pct
        style_weight[style["style"]] += weight_pct

    return {
        "size_exposure": dict(size_weight),
        "style_exposure": dict(style_weight),
        "snapshot_id": snap.id,
    }
```

Run: `cd backend && python -m pytest tests/test_factor_style.py -v` → 4 pass
Commit: `feat: add fund style factor classification (size/value)`

### Task 2: 风格暴露 API

**Files:**
- Create: `backend/tests/test_api_style.py`
- Modify: `backend/app/api/routes/analysis.py`

`backend/tests/test_api_style.py`:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_style_exposure_empty():
    response = client.get("/api/analysis/style-exposure")
    assert response.status_code == 200
    data = response.json()
    assert "size_exposure" in data
    assert "style_exposure" in data
```

In `routes/analysis.py`, add:
```python
from app.services.factor_style import compute_portfolio_style

@router.get("/style-exposure")
def style_exposure(session: Session = Depends(get_db)):
    return compute_portfolio_style(session)
```

Run: `cd backend && python -m pytest tests/test_api_style.py tests/ -x -q` → all pass
Commit: `feat: add GET /api/analysis/style-exposure`

### Task 3: 宏观环境感知

**Files:**
- Create: `backend/tests/test_macro.py`
- Create: `backend/app/services/macro.py`

`backend/tests/test_macro.py`:
```python
from app.services.macro import classify_environment


def test_rising_yields_tight():
    assert classify_environment(3.5, 2.8, 2.0) == "tight"


def test_falling_yields_loose():
    assert classify_environment(2.5, 3.0, 1.0) == "loose"


def test_stable_neutral():
    assert classify_environment(2.85, 2.80, 1.5) == "neutral"
```

`backend/app/services/macro.py`:
```python
"""Macro environment indicators via akshare."""

import logging
from app.services.http_retry import _with_retry

logger = logging.getLogger(__name__)


def classify_environment(bond_10y: float, bond_10y_60d_ago: float, shibor: float) -> str:
    """Classify macro environment as tight/neutral/loose."""
    rate_change = bond_10y - bond_10y_60d_ago
    if rate_change > 0.3 and shibor > 1.8:
        return "tight"
    elif rate_change < -0.3 and shibor < 1.5:
        return "loose"
    return "neutral"


def fetch_macro_indicators() -> dict:
    """Fetch current macro indicators. Returns dict with keys:
    bond_10y, bond_10y_60d_ago, shibor_overnight, environment, available
    """
    try:
        import akshare as ak

        # 10-year govt bond yield
        bond_df = ak.bond_china_yield()
        bond_10y = float(bond_df.iloc[-1]["10年期国债收益率"])
        bond_10y_60d = float(bond_df.iloc[-60]["10年期国债收益率"]) if len(bond_df) >= 60 else bond_10y

        # Shibor
        shibor_df = ak.shibor_rate()
        shibor_on = float(shibor_df.iloc[0]["利率"]) if len(shibor_df) > 0 else 1.5

        env = classify_environment(bond_10y, bond_10y_60d, shibor_on)

        return {
            "bond_10y": round(bond_10y, 2),
            "bond_10y_trend": "rising" if bond_10y > bond_10y_60d + 0.1 else (
                "falling" if bond_10y < bond_10y_60d - 0.1 else "stable"
            ),
            "shibor_overnight": round(shibor_on, 2),
            "environment": env,
            "available": True,
        }
    except Exception as exc:
        logger.warning("Failed to fetch macro indicators: %s", exc)
        return {"available": False, "environment": "unknown"}
```

Add API in `routes/analysis.py`:
```python
from app.services.macro import fetch_macro_indicators

@router.get("/macro")
def macro_indicators():
    return fetch_macro_indicators()
```

Run: `cd backend && python -m pytest tests/test_macro.py tests/ -x -q` → all pass
Commit: `feat: add macro environment indicators and API`

### Task 4: 前端分析页集成

**Files:**
- Modify: `frontend/src/pages/AnalysisPage.tsx`
- Modify: `frontend/src/types/index.ts`

1. Add types to `types/index.ts`:
```typescript
export interface StyleExposure {
  size_exposure: Record<string, number>
  style_exposure: Record<string, number>
  snapshot_id: number | null
}

export interface MacroIndicators {
  bond_10y: number | null
  bond_10y_trend: string
  shibor_overnight: number | null
  environment: string
  available: boolean
}
```

2. Add query functions in `queries.ts`:
```typescript
export async function fetchStyleExposure() {
  return api.get<import('../types').StyleExposure>('/api/analysis/style-exposure')
}

export async function fetchMacroIndicators() {
  return api.get<import('../types').MacroIndicators>('/api/analysis/macro')
}
```

3. Add hooks in `hooks.ts`:
```typescript
export function useStyleExposure() {
  return useQuery({ queryKey: queryKeys.styleExposure, queryFn: fetchStyleExposure })
}
export function useMacroIndicators() {
  return useQuery({ queryKey: queryKeys.macro, queryFn: fetchMacroIndicators })
}
```

4. Add query keys in `queries.ts`:
```typescript
styleExposure: ['styleExposure'] as const,
macro: ['macro'] as const,
```

5. In AnalysisPage, add macro indicator bar at top and style exposure section.

### Task 5: 模拟调仓 WhatIfPanel

**Files:**
- Create: `frontend/src/components/WhatIfPanel.tsx`
- Modify: `frontend/src/pages/AnalysisPage.tsx`

`WhatIfPanel.tsx`: Pure frontend component that takes current `overview` and `correlation` data, with two FundSearchCombobox dropdowns (source/target), amount input, and computes Before/After comparison for category allocation changes.

Embed into AnalysisPage below the existing sections.

### Task 6: 回归验证

Run backend tests + frontend build. Move plan to completed. Update README.
