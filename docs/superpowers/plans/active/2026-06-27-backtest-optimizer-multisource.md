# v2.1 历史回测+组合优化器+多数据源 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> **Status:** active | **Created:** 2026-06-27
> **Spec:** docs/superpowers/specs/active/2026-06-27-backtest-optimizer-multisource-design.md

**Goal:** 历史信号回测验证、均值方差组合优化、tushare备用数据源

---

### Task 1: 历史回测引擎

**Files:**
- Create: `backend/tests/test_backtest_engine.py`
- Create: `backend/app/services/backtest_engine.py`
- Modify: `backend/app/api/routes/backtest.py`

`backtest_engine.py`: New function `run_history_backtest(session)` that:
1. Gets all historical snapshots
2. For each snapshot, re-runs signal engine
3. Computes what the portfolio would look like if signals were followed
4. Compares with actual subsequent snapshot values

Return simplified backtest report: `{snapshots_tested, signals_generated, hit_rate, avg_excess_return}`

Add `POST /api/backtest/run` to routes/backtest.py.

Frontend: Add a "运行回测" button in BacktestPanel, display results.

### Task 2: 组合优化器

**Files:**
- Create: `backend/tests/test_optimizer.py`
- Create: `backend/app/services/optimizer.py`
- Modify: `backend/app/api/routes/analysis.py`

`optimizer.py`: Use scipy.optimize.minimize to minimize portfolio variance given:
- Fund expected returns (from cached metrics)
- Covariance matrix (from NAV history)
- Constraints: weights sum to 1, within category target ± deviation

Add `POST /api/analysis/optimize` endpoint. No frontend this round.

### Task 3: 多数据源后备

**Files:**
- Modify: `backend/app/services/data_sync.py`

Add `fetch_nav_fallback(code)` that tries akshare first, falls back to tushare on failure. Tushare token from env `TUSHARE_TOKEN`. On failure of both, raise. Simple try/except chain.

### Task 4: 回归 + 归档

Run all tests, build frontend, archive plan, update README.
