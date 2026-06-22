# v1.1 Dashboard + 导入体验 + 同步闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

> **Status:** completed
> **Created:** 2026-06-21
> **Spec:** docs/superpowers/specs/active/2026-06-21-fund-quant-assistant-design.md
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Based on:** docs/superpowers/plans/completed/2026-06-21-alipay-ocr-formats.md

**Goal:** 补全 Dashboard 可视化（大类饼图 + Top5 集中度）、提升 OCR 确认体验、导入成功后一键同步并跳转信号页。

**Architecture:** 扩展 `GET /api/portfolio/overview` 返回 `category_allocation` / `top_holdings` / `concentration_top5_pct`；OCR upload 每行附带 `warnings`；前端 Recharts 饼图 + 导入成功态引导 sync。

**Tech Stack:** FastAPI, fund_classifier, pytest | React, Recharts, Tailwind

---

### Task 1: Overview API 扩展

**Files:**
- Modify: `backend/app/schemas/portfolio.py`, `backend/app/repositories/portfolio.py`
- Test: `backend/tests/test_api_portfolio.py`

- [x] **Step 1: `CategoryAllocationOut` + Overview 新字段**
- [x] **Step 2: `_build_category_allocation` 用 fund_classifier + FundMetadata**
- [x] **Step 3: `top_holdings` Top5 + `concentration_top5_pct`**
- [x] **Step 4: `test_overview_category_allocation_and_concentration`**

---

### Task 2: OCR 行级 warnings

**Files:**
- Modify: `backend/app/schemas/ocr.py`, `backend/app/api/routes/ocr.py`

- [x] **Step 1: `ParsedHoldingOut.warnings`**
- [x] **Step 2: upload 响应每行附带 validate 结果**

---

### Task 3: Dashboard 可视化

**Files:**
- Create: `frontend/src/components/AllocationChart.tsx`, `ConcentrationCard.tsx`
- Modify: `frontend/src/pages/Dashboard.tsx`, `frontend/src/types/index.ts`

- [x] **Step 1: Recharts 环形饼图 + 图例**
- [x] **Step 2: Top5 进度条列表**
- [x] **Step 3: Dashboard 两列布局接入**
- [x] **Step 4（v1.1.1 polish）:** `chartColors.ts` 共享 8 色分类色板；饼图/Top5 进度条弃用 slate 灰阶；Top5 合计卡 indigo/sky 渐变 — 见 spec「Dashboard 可视化样式」

---

### Task 4: 导入体验

**Files:**
- Modify: `frontend/src/pages/ImportPage.tsx`

- [x] **Step 1: 缺代码/警告行 amber 高亮 + 行内 warnings**
- [x] **Step 2: 删行按钮**
- [x] **Step 3: 收益率百分比编辑（存储仍为小数）**

---

### Task 5: 导入后同步闭环

**Files:**
- Modify: `frontend/src/pages/ImportPage.tsx`

- [x] **Step 1: 确认成功后展示 success 面板**
- [x] **Step 2: 「同步数据并查看信号」→ syncData + navigate /signals**
- [x] **Step 3: 「查看总览」次要按钮**

---

### Task 6: Polish

- [x] **Step 1: HoldingsTable 按权重降序**
- [x] **Step 2: pytest + frontend build 通过**
- [x] **Step 3: 更新 spec Changelog 与本 plan**

---

## Spec 覆盖自检

| 需求 | Task |
|------|------|
| Dashboard 大类饼图 | 1, 3 |
| Top5 集中度 | 1, 3 |
| 导入行级警告/删行 | 2, 4 |
| 导入后 sync 闭环 | 5 |
