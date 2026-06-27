# v2.5 今日盈亏与净值异动 Implementation Plan

> **Status:** completed
> **Created:** 2026-06-27
> **Spec:** docs/superpowers/specs/active/2026-06-27-nav-daily-change-design.md

**Goal:** Dashboard 展示今日盈亏与净值异动预警，延续 v2.4 实时估值能力。

**Architecture:** build_overview 查最新+上一日净值 → 计算 daily_profit 与 nav_anomalies → Schema/API 扩展 → 前端 StatCard + 横幅 + 5 分钟轮询。

**Tech Stack:** Python 3.11+ / FastAPI / SQLModel, TypeScript / React / TanStack Query

---

### Task 1: Schema 扩展

**Files:** `backend/app/schemas/portfolio.py`

- [x] `NavAnomalyOut` 新增
- [x] `HoldingOut` 新增 `daily_profit`, `nav_change_pct`, `prev_nav_date`
- [x] `OverviewOut` 新增 `daily_total_profit`, `nav_anomalies`

### Task 2: build_overview 增强

**Files:** `backend/app/repositories/portfolio.py`

- [x] `_fetch_prev_nav_map()` 查上一交易日净值
- [x] 计算 holding / portfolio daily_profit
- [x] 15% 阈值检测 nav_anomalies（复用 `NAV_DAILY_CHANGE_THRESHOLD`）

### Task 3: 测试

**Files:** `backend/tests/test_holdings_revalue.py`

- [x] 两日净值 → daily 字段正确
- [x] 单日净值 → daily null
- [x] 16% 跳变 → anomaly 列表非空

### Task 4: 前端

**Files:** `frontend/src/types/index.ts`, `frontend/src/api/hooks.ts`, `frontend/src/pages/Dashboard.tsx`, `frontend/src/components/HoldingsTable.tsx`, `frontend/src/components/NavAnomalyBanner.tsx`

- [x] 类型同步
- [x] `useOverviewLive` refetchInterval 5min
- [x] Dashboard 今日盈亏卡片 + 异动横幅
- [x] HoldingsTable 今日盈亏列

### Task 5: 文档索引

**Files:** `docs/superpowers/README.md`

- [x] 添加 v2.5 索引行
