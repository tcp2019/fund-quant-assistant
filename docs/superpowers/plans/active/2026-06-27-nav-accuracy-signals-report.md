# v1.8 NAV复权+业绩增强+定期报告 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** active
> **Created:** 2026-06-27
> **Spec:** docs/superpowers/specs/active/2026-06-27-nav-accuracy-signals-report-design.md
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Based on:** none

**Goal:** NAV复权修正收益率计算、新增4个业绩指标、新增周报Markdown导出

**Architecture:** 子系统A修改analysis.py和metrics_cache.py统一用累计净值；子系统B新增performance_metrics.py并在performance.py中集成4个新rule；子系统C新增report路由和前端导出按钮

**Tech Stack:** Python 3.11+ / FastAPI / SQLModel / SQLite / numpy, React 19 / TypeScript / TanStack Query

---

### Task 1: _aligned_nav_series 增加 use_acc_nav 参数

**Files:**
- Create: `backend/tests/test_nav_acc_usage.py`
- Modify: `backend/app/services/analysis.py`

- [ ] **Step 1: Write test**

`backend/tests/test_nav_acc_usage.py`:
```python
from unittest.mock import patch
from sqlmodel import Session
from app.db.models import FundNavHistory, Holding, PortfolioSnapshot
from app.services.analysis import _aligned_nav_series


def test_aligned_nav_series_uses_acc_nav_by_default(session: Session):
    snap = PortfolioSnapshot()
    session.add(snap)
    session.commit()

    h = Holding(snapshot_id=snap.id, fund_code="110011", fund_name="测试",
                shares=100, cost_price=1.0, market_value=100)
    session.add(h)
    session.commit()

    session.add(FundNavHistory(code="110011", date="2026-01-01", nav=1.0, acc_nav=2.0))
    session.add(FundNavHistory(code="110011", date="2026-01-02", nav=0.5, acc_nav=2.1))
    session.commit()

    labels, series = _aligned_nav_series(session, ["110011"], 90)
    assert len(series) == 1
    # Should use acc_nav (2.0, 2.1) not nav (1.0, 0.5 with a 50% fake drop)
    assert series[0] == [2.0, 2.1]


def test_aligned_nav_series_falls_back_to_nav(session: Session):
    snap = PortfolioSnapshot()
    session.add(snap)
    session.commit()

    h = Holding(snapshot_id=snap.id, fund_code="110011", fund_name="测试",
                shares=100, cost_price=1.0, market_value=100)
    session.add(h)
    session.commit()

    session.add(FundNavHistory(code="110011", date="2026-01-01", nav=1.0, acc_nav=0.0))
    session.add(FundNavHistory(code="110011", date="2026-01-02", nav=1.05, acc_nav=0.0))
    session.commit()

    labels, series = _aligned_nav_series(session, ["110011"], 90)
    # acc_nav is 0.0 (invalid), should fall back to nav
    assert series[0] == [1.0, 1.05]
```

- [ ] **Step 2: Run test to verify it fails**

`cd backend && python -m pytest tests/test_nav_acc_usage.py -v`
Expected: FAIL (uses nav, not acc_nav)

- [ ] **Step 3: Modify _aligned_nav_series**

In `backend/app/services/analysis.py`, change `_nav_by_date` to also read acc_nav, and modify `_aligned_nav_series`:

```python
def _nav_by_date(session: Session, code: str, use_acc_nav: bool = True) -> dict[str, float]:
    rows = session.exec(
        select(FundNavHistory)
        .where(FundNavHistory.code == code)
        .order_by(FundNavHistory.date)
    ).all()
    if use_acc_nav:
        # Use acc_nav if all values > 0; fall back to nav otherwise
        vals = {row.date: row.acc_nav for row in rows}
        if vals and all(v > 0 for v in vals.values()):
            return vals
    return {row.date: row.nav for row in rows}


def _aligned_nav_series(
    session: Session,
    fund_codes: list[str],
    lookback_trading_days: int,
    use_acc_nav: bool = True,
) -> tuple[list[str], list[list[float]]]:
    if not fund_codes:
        return [], []

    nav_maps = {code: _nav_by_date(session, code, use_acc_nav) for code in fund_codes}
    # ... rest unchanged
```

Update `compute_correlation` and `compute_risk` calls to pass `use_acc_nav=True` (or omit, since it's the default).

- [ ] **Step 4: Run tests**

`cd backend && python -m pytest tests/test_nav_acc_usage.py -v`
Expected: PASS (2 tests)
`cd backend && python -m pytest tests/ -x -q`
Expected: all existing tests pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/analysis.py backend/tests/test_nav_acc_usage.py
git commit -m "feat: use acc_nav (累计净值) for correlation and risk calculations"
```

---

### Task 2: metrics_cache 改用 acc_nav

**Files:**
- Modify: `backend/app/services/metrics_cache.py`

- [ ] **Step 1: Change navs to acc_navs**

In `compute_and_cache_metrics`, change line 22:
```python
# Before: navs = [row.nav for row in rows]
# After:
navs = [row.acc_nav if row.acc_nav > 0 else row.nav for row in rows]
```

Also update the existing tests to verify acc_nav usage:

In `backend/tests/test_metrics_cache.py`, add:
```python
def test_metrics_cache_uses_acc_nav(session):
    session.add(FundNavHistory(code="110011", date="2026-01-01", nav=1.0, acc_nav=2.0))
    session.add(FundNavHistory(code="110011", date="2026-06-20", nav=0.8, acc_nav=2.4))
    session.commit()

    from app.services.metrics_cache import compute_and_cache_metrics
    cache = compute_and_cache_metrics(session, "110011")
    # return_1y = (2.4 / 2.0) - 1 = 0.20 (20% using acc_nav)
    # If nav was used: (0.8 / 1.0) - 1 = -0.20 (-20% wrong!)
    assert cache is not None
    assert cache.return_1y is not None
    assert cache.return_1y > 0  # Should be positive with acc_nav
```

- [ ] **Step 2: Run tests**

`cd backend && python -m pytest tests/test_metrics_cache.py -v`
Expected: PASS (3 tests)

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/metrics_cache.py backend/tests/test_metrics_cache.py
git commit -m "fix: use acc_nav in metrics_cache for correct return calculation"
```

---

### Task 3: 新增 performance_metrics.py（4个指标函数）

**Files:**
- Create: `backend/tests/test_performance_metrics.py`
- Create: `backend/app/services/signals/performance_metrics.py`

- [ ] **Step 1: Write tests first**

`backend/tests/test_performance_metrics.py`:
```python
import numpy as np
from app.services.signals.performance_metrics import (
    calmar_ratio,
    downside_capture,
    info_ratio,
    rolling_sharpe,
)


def test_rolling_sharpe_positive():
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.01, 120)  # 120 days of small positive returns
    rs = rolling_sharpe(returns, window=60)
    assert rs > 0  # positive returns → positive sharpe


def test_rolling_sharpe_insufficient_data():
    returns = np.array([0.01, 0.02])  # only 2 points
    rs = rolling_sharpe(returns, window=60)
    assert rs == 0.0


def test_calmar_ratio():
    navs = [1.0, 1.01, 1.02, 1.015, 1.03, 1.04]  # mild growth, small drawdown
    calmar = calmar_ratio(navs)
    assert calmar > 0


def test_calmar_ratio_negative():
    navs = [1.0, 0.95, 0.93, 0.90, 0.88, 0.85]  # steady decline
    calmar = calmar_ratio(navs)
    assert calmar < 0


def test_downside_capture():
    fund_rets = np.array([0.01, -0.02, 0.01, -0.03, 0.02, -0.01])
    bench_rets = np.array([0.005, -0.01, 0.005, -0.02, 0.01, -0.005])
    dc = downside_capture(fund_rets, bench_rets)
    # Fund dropped more than benchmark → capture > 100%
    assert dc > 100.0


def test_info_ratio():
    fund_rets = np.array([0.02, 0.01, 0.015, 0.005, 0.02])
    bench_rets = np.array([0.01, 0.01, 0.01, 0.01, 0.01])
    ir = info_ratio(fund_rets, bench_rets)
    assert ir > 0  # fund outperforms benchmark
```

- [ ] **Step 2: Run test to verify it fails**

`cd backend && python -m pytest tests/test_performance_metrics.py -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Implement performance_metrics.py**

```python
"""Additional performance quality indicators for signal engine."""
from __future__ import annotations

import numpy as np

from app.services.metrics import daily_returns_from_navs, max_drawdown, sharpe_ratio


def rolling_sharpe(returns: np.ndarray, window: int = 60) -> float:
    """Average of rolling-window Sharpe ratios. Returns 0 if insufficient data."""
    if len(returns) < window:
        return 0.0
    annual_factor = np.sqrt(252)
    sharpe_values = []
    for i in range(window, len(returns) + 1):
        window_rets = returns[i - window : i]
        std = window_rets.std(ddof=1)
        if std == 0:
            continue
        sharpe_values.append(window_rets.mean() / std * annual_factor)
    return float(np.mean(sharpe_values)) if sharpe_values else 0.0


def calmar_ratio(nav_series: list[float]) -> float:
    """Annualized return / max drawdown. Higher is better."""
    if len(nav_series) < 2:
        return 0.0
    navs = np.asarray(nav_series, dtype=float)
    returns = navs[1:] / navs[:-1] - 1
    annual_return = float(returns.mean() * 252)
    dd = max_drawdown(returns)
    if dd == 0 or dd >= 0:
        return 0.0
    return annual_return / abs(dd)


def downside_capture(
    fund_returns: np.ndarray,
    benchmark_returns: np.ndarray,
) -> float:
    """Ratio of fund's downside returns to benchmark's downside returns."""
    if len(fund_returns) < 2 or len(benchmark_returns) < 2:
        return 100.0
    min_len = min(len(fund_returns), len(benchmark_returns))
    fund = fund_returns[-min_len:]
    bench = benchmark_returns[-min_len:]
    down_mask = bench < 0
    if not down_mask.any():
        return 100.0
    fund_down = fund[down_mask].mean()
    bench_down = bench[down_mask].mean()
    if bench_down == 0:
        return 100.0
    return float((fund_down / bench_down) * 100)


def info_ratio(
    fund_returns: np.ndarray,
    benchmark_returns: np.ndarray,
) -> float:
    """Excess return over benchmark / tracking error."""
    if len(fund_returns) < 2 or len(benchmark_returns) < 2:
        return 0.0
    min_len = min(len(fund_returns), len(benchmark_returns))
    fund = fund_returns[-min_len:]
    bench = benchmark_returns[-min_len:]
    excess = fund - bench
    std = excess.std(ddof=1)
    if std == 0:
        return 0.0
    return float(excess.mean() / std * np.sqrt(252))
```

- [ ] **Step 4: Run tests**

`cd backend && python -m pytest tests/test_performance_metrics.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/signals/performance_metrics.py backend/tests/test_performance_metrics.py
git commit -m "feat: add rolling_sharpe, calmar_ratio, downside_capture, info_ratio"
```

---

### Task 4: 集成新指标到 compute_performance_signals

**Files:**
- Create: `backend/tests/test_performance_enhanced.py`
- Modify: `backend/app/services/signals/performance.py`

- [ ] **Step 1: Write test for new rules**

`backend/tests/test_performance_enhanced.py`:
```python
from app.services.signals.performance import compute_performance_signals


def test_low_rolling_sharpe_triggers_reduce():
    metrics = {"110011": {"sharpe_1y": 0.3, "excess_return_1y": -0.08}}
    signals = compute_performance_signals(["110011"], metrics)
    assert len(signals) == 1
    assert any(r["rule"] == "sharpe_1y" for r in signals[0]["reasons"])


def test_multiple_good_indicators_produce_hold():
    metrics = {"110011": {"sharpe_1y": 1.5, "excess_return_1y": 0.05, "max_drawdown_1y": -0.05}}
    signals = compute_performance_signals(["110011"], metrics)
    assert signals[0]["signal_type"] in ("hold", "watch")


def test_all_new_rules_integrated():
    """Verify new rule names are recognized in output."""
    metrics = {
        "110011": {
            "sharpe_1y": 0.2,
            "max_drawdown_1y": -0.35,
            "excess_return_1y": -0.12,
            "rolling_sharpe": 0.3,
            "calmar": 0.15,
            "downside_capture": 140.0,
            "info_ratio": -0.8,
        }
    }
    signals = compute_performance_signals(["110011"], metrics)
    rules = [r["rule"] for r in signals[0]["reasons"]]
    assert "low_rolling_sharpe" in rules
    assert "low_calmar" in rules
    assert "high_downside_capture" in rules
    assert "low_info_ratio" in rules
```

- [ ] **Step 2: Run test to verify it fails**

`cd backend && python -m pytest tests/test_performance_enhanced.py -v`
Expected: FAIL (new rules not yet in signal output)

- [ ] **Step 3: Add new rules to performance.py**

In `backend/app/services/signals/performance.py`, add new thresholds at the top:

```python
ROLLING_SHARPE_MIN = 0.5
CALMAR_MIN = 0.3
DOWNSIDE_CAPTURE_MAX = 120.0
INFO_RATIO_MIN = -0.5
```

Then inside the `for code in fund_codes` loop, after the existing max_dd check (around line 61-68), add:

```python
rolling_sharpe_val = metrics.get("rolling_sharpe")
if rolling_sharpe_val is not None and rolling_sharpe_val < ROLLING_SHARPE_MIN:
    reasons.append(
        {
            "layer": "performance",
            "rule": "low_rolling_sharpe",
            "detail": f"滚动夏普 {rolling_sharpe_val:.2f}，低于阈值 {ROLLING_SHARPE_MIN}，收益不稳定",
        }
    )

calmar_val = metrics.get("calmar")
if calmar_val is not None and calmar_val < CALMAR_MIN:
    reasons.append(
        {
            "layer": "performance",
            "rule": "low_calmar",
            "detail": f"Calmar比率 {calmar_val:.2f}，低于阈值 {CALMAR_MIN}，回撤风险偏高",
        }
    )

downside_cap = metrics.get("downside_capture")
if downside_cap is not None and downside_cap > DOWNSIDE_CAPTURE_MAX:
    reasons.append(
        {
            "layer": "performance",
            "rule": "high_downside_capture",
            "detail": f"下行捕获率 {downside_cap:.0f}%，高于 {DOWNSIDE_CAPTURE_MAX:.0f}%，跌时比基准跌得多",
        }
    )

info_r = metrics.get("info_ratio")
if info_r is not None and info_r < INFO_RATIO_MIN:
    reasons.append(
        {
            "layer": "performance",
            "rule": "low_info_ratio",
            "detail": f"信息比率 {info_r:.2f}，低于阈值 {INFO_RATIO_MIN}，主动管理贡献不足",
        }
    )
```

Also update the aggregation logic at lines 81-96: change the condition for `"reduce"` to also trigger if 3+ reasons (was 2+):

```python
if not reasons:
    signal_type = "hold"
    detail = "业绩质量正常"
elif (
    len(reasons) >= 3
    or ...
```

- [ ] **Step 4: Run tests**

`cd backend && python -m pytest tests/test_performance_enhanced.py tests/test_signals_performance.py -v`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/signals/performance.py backend/tests/test_performance_enhanced.py
git commit -m "feat: integrate rolling_sharpe, calmar, downside_capture, info_ratio into performance signals"
```

---

### Task 5: 信号引擎计算新指标并传入 metrics

**Files:**
- Modify: `backend/app/services/signals/engine.py`

- [ ] **Step 1: Compute new metrics in _load_metrics**

In `engine.py`, modify `_load_metrics` (or the section that builds metrics dict before calling `compute_performance_signals`) to also compute the new indicators.

Add after the existing metrics retrieval:

```python
from app.services.signals.performance_metrics import (
    calmar_ratio,
    downside_capture,
    info_ratio,
    rolling_sharpe,
)
from app.services.metrics import daily_returns_from_navs

# Inside the metrics-building loop:
nav_rows = session.exec(
    select(FundNavHistory)
    .where(FundNavHistory.code == code)
    .order_by(FundNavHistory.date.asc())
).all()

if len(nav_rows) >= 60:
    navs = [row.acc_nav if row.acc_nav > 0 else row.nav for row in nav_rows]
    returns = daily_returns_from_navs(navs)
    if len(returns) >= 60:
        metrics["rolling_sharpe"] = round(rolling_sharpe(returns), 4)
        metrics["calmar"] = round(calmar_ratio(navs), 4)
```

- [ ] **Step 2: Run full test suite**

`cd backend && python -m pytest tests/test_signals_engine.py -v`
Expected: all existing engine tests pass

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/signals/engine.py
git commit -m "feat: compute new performance metrics in signal engine"
```

---

### Task 6: 新增周报 API 端点

**Files:**
- Create: `backend/tests/test_report_weekly.py`
- Create: `backend/app/api/routes/report.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write test**

`backend/tests/test_report_weekly.py`:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_weekly_report_returns_markdown():
    response = client.get("/api/report/weekly")
    # No snapshot data → 200 with empty template
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    text = response.text
    assert "# 基金组合周报" in text
    assert "暂无数据" in text


def test_weekly_report_with_snapshot_id():
    response = client.get("/api/report/weekly?snapshot_id=99999")
    assert response.status_code == 200
    text = response.text
    assert "# 基金组合周报" in text
```

- [ ] **Step 2: Run test to verify it fails**

`cd backend && python -m pytest tests/test_report_weekly.py -v`
Expected: FAIL (404, route doesn't exist)

- [ ] **Step 3: Create report route**

`backend/app/api/routes/report.py`:
```python
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from app.api.deps import get_db
from app.repositories.portfolio import build_overview, get_latest_snapshot
from app.services.signals.engine import SignalRecord
from app.services.theme_heat import rank_hot_themes

router = APIRouter(prefix="/api/report", tags=["report"])

WEEKLY_REPORT_TEMPLATE = """# 基金组合周报

> 本报告由量化规则自动生成，仅供个人参考，**不构成投资建议**。

---

## 组合概览

{overview_section}

## 本周信号

{signals_section}

## 大类配置

{allocation_section}

## 热点主题

{themes_section}

## 风险指标

{risk_section}

---

*报告生成时间：{generated_at}*
"""


@router.get("/weekly", response_class=PlainTextResponse)
def weekly_report(
    snapshot_id: int | None = Query(None),
    session: Session = Depends(get_db),
):
    from datetime import datetime, timezone

    snap = get_latest_snapshot(session) if snapshot_id is None else session.get(
        __import__("app.db.models").PortfolioSnapshot, snapshot_id
    )

    if snap is None:
        return WEEKLY_REPORT_TEMPLATE.format(
            overview_section="> 暂无数据，请先导入持仓并同步数据。",
            signals_section="> 暂无信号数据。",
            allocation_section="> 暂无配置数据。",
            themes_section="> 暂无热点数据。",
            risk_section="> 暂无风险数据。",
            generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        )

    try:
        overview = build_overview(session)
    except Exception:
        overview = None

    # Overview section
    if overview and overview.holdings:
        overview_section = f"""- **快照：** #{overview.snapshot_id}
- **总市值：** ¥{overview.total_value:,.0f}
- **总盈亏：** ¥{overview.total_profit:,.0f}（{overview.total_profit_rate * 100:.2f}%）
- **持仓基金数：** {len(overview.holdings)} 只
- **净值截至：** {overview.data_as_of_date or '未知'}"""
    else:
        overview_section = "> 暂无组合数据。"

    # Signals
    try:
        signals = session.exec(
            __import__("sqlmodel").select(SignalRecord)
            .where(SignalRecord.snapshot_id == snap.id)
        ).all()
        add_count = sum(1 for s in signals if s.signal_type == "add")
        reduce_count = sum(1 for s in signals if s.signal_type == "reduce")
        watch_count = sum(1 for s in signals if s.signal_type == "watch")
        signals_section = f"""- **增配信号：** {add_count} 条
- **减仓信号：** {reduce_count} 条
- **观察信号：** {watch_count} 条"""
    except Exception:
        signals_section = "> 暂无信号数据。"

    # Allocation
    if overview and overview.category_allocation:
        allocation_section = "\n".join(
            f"- {a.label}: {a.weight_pct:.1f}%"
            for a in overview.category_allocation
        )
    else:
        allocation_section = "> 暂无配置数据。"

    # Hot themes
    try:
        themes = rank_hot_themes(session, limit=5)
        if themes:
            themes_section = "\n".join(
                f"- {t.label}: 近1月中位数 {t.return_1m_median:.2f}%"
                for t in themes[:5]
            )
        else:
            themes_section = "> 暂无热点数据。"
    except Exception:
        themes_section = "> 暂无热点数据。"

    # Risk
    try:
        from app.services.analysis import compute_risk
        risk = compute_risk(session)
        risk_section = f"""- **组合波动率：** {risk.get('volatility') or 'N/A'}
- **夏普比率：** {risk.get('sharpe') or 'N/A'}
- **最大回撤：** {risk.get('max_dd') or 'N/A'}"""
    except Exception:
        risk_section = "> 暂无风险数据。"

    return WEEKLY_REPORT_TEMPLATE.format(
        overview_section=overview_section,
        signals_section=signals_section,
        allocation_section=allocation_section,
        themes_section=themes_section,
        risk_section=risk_section,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )
```

In `backend/app/main.py`, register the router (add near other router registrations):

```python
from app.api.routes.report import router as report_router

app.include_router(report_router)
```

- [ ] **Step 4: Run tests**

`cd backend && python -m pytest tests/test_report_weekly.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/report.py backend/app/main.py backend/tests/test_report_weekly.py
git commit -m "feat: add GET /api/report/weekly endpoint returning Markdown"
```

---

### Task 7: 前端 Dashboard 导出周报按钮

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Add export button**

Add after the snapshot info `<p>` tag, before the `<ActionSummaryCards>`:

```tsx
import { api } from '../api/client'

// Add inside the component:
async function handleExportReport() {
  try {
    const response = await fetch('/api/report/weekly')
    const text = await response.text()
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `fund-report-${new Date().toISOString().slice(0, 10)}.md`
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    // silently fail
  }
}
```

In the JSX, add button in the header area:

```tsx
<div className="flex items-center justify-between">
  <div>
    <h2 className="text-2xl font-semibold text-slate-900">组合总览</h2>
    <p className="mt-1 text-sm text-slate-500">...</p>
  </div>
  <button
    type="button"
    onClick={handleExportReport}
    className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
  >
    📥 导出周报
  </button>
</div>
```

- [ ] **Step 2: Verify build**

`cd frontend && npx tsc -b --noEmit && npm run build`
Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: add weekly report export button on Dashboard"
```

---

### Task 8: 回归验证 + README

**Files:**
- None (verification only)
- Modify: `docs/superpowers/README.md`

- [ ] **Step 1: Run full test suite**

`cd backend && python -m pytest tests -x -q`
Expected: all tests pass

- [ ] **Step 2: Run frontend build**

`cd frontend && npm run build`
Expected: build succeeds

- [ ] **Step 3: Move plan to completed, update README**

```bash
mv docs/superpowers/plans/active/2026-06-27-nav-accuracy-signals-report.md docs/superpowers/plans/completed/
```

Update plan status to `completed` and README index row.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/ && git commit -m "docs: v1.8 plan completed"
```
