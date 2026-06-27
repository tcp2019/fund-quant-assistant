# v2.4 净值实时化 Implementation Plan

> **Status:** completed
> **Created:** 2026-06-27
> **Spec:** docs/superpowers/specs/active/2026-06-27-nav-realtime-design.md

**Goal:** 持仓盈亏用最新净值动态重算，Dashboard 展示实时市值/盈亏。

**Architecture:** build_overview() 批量查询 FundNavHistory 最新净值 → 重算 current_value/current_profit → Schema 扩展 → 前端展示。

**Tech Stack:** Python 3.13+ / FastAPI / SQLModel / SQLAlchemy, TypeScript / React 19 / Tailwind CSS

---

### Task 1: Schema 扩展

**Files:** `backend/app/schemas/portfolio.py`

- [x] HoldingOut 新增 `current_value`, `current_profit`, `nav_date`
- [x] OverviewOut 新增 `current_total_value`, `current_total_profit`, `current_total_profit_rate`, `nav_date`

### Task 2: build_overview 增强

**Files:** `backend/app/repositories/portfolio.py`

- [x] 批量查询最新净值（subquery join FundNavHistory）
- [x] 每只持仓计算实时市值/盈亏
- [x] 汇总 real-time 总市值/总盈亏/收益率
- [x] 无净值时回退到快照值
- [x] `_holding_to_out()` 接受 current_* 参数

### Task 3: 前端类型

**Files:** `frontend/src/types/index.ts`

- [x] Holding 新增 `current_value`, `current_profit`, `nav_date`
- [x] Overview 新增 `current_total_value`, `current_total_profit`, `current_total_profit_rate`, `nav_date`

### Task 4: Dashboard 展示

**Files:** `frontend/src/pages/Dashboard.tsx`

- [x] StatCard: 有实时值 → 显示"实时市值"/"实时盈亏" + 快照对照
- [x] Header: nav_date 优先于 data_as_of_date

### Task 5: HoldingsTable 增强

**Files:** `frontend/src/components/HoldingsTable.tsx`

- [x] 有实时值 → 市值列显示实时值 + 导入值小字对照
- [x] 盈亏/收益率联动实时值

### Task 6: 测试

**Files:** `backend/tests/test_holdings_revalue.py`

- [x] 有净值 → current_* 正确计算
- [x] 无净值 → 回退到快照值
