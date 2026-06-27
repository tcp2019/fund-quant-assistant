# v2.6 产品收敛 · 普通投资者体验 Implementation Plan

> **Status:** completed
> **Created:** 2026-06-27
> **Spec:** docs/superpowers/specs/active/2026-06-27-retail-ux-convergence-design.md

**Goal:** 7 页收敛为 4 主导航 + 深入了解二级页，白话文案，不动后端引擎。

**Architecture:** AdvicePage 合并 opportunities+signals；Dashboard 精简；InsightsPage 降级分析+热点；Layout 导航与 legacy redirect；Settings 高级折叠。

**Tech Stack:** React 19 / React Router / Tailwind；无后端变更

---

### Task 1: 路由与导航骨架

- [x] Layout 4 项主导航 + Header 品牌文案
- [x] App.tsx `/advice`、`/insights` + legacy redirect
- [x] `npm run build`

### Task 2: AdvicePage

- [x] 合并 StructuralAlerts + ActionList + SignalsTable(details)
- [x] sync / 空态 / `?tab=all` 展开

### Task 3: Dashboard 精简

- [x] AdviceSummary 替代 ActionSummaryCards + HotThemeRadar
- [x] 大类饼图 + 折叠持仓/集中度 + 底部链接

### Task 4: InsightsPage

- [x] Tab: risk / themes / backtest
- [x] `/opportunities?tab=themes` → `/insights?tab=themes`

### Task 5: Settings 分区

- [x] 风险偏好基础区 + `<details>` 高级策略

### Task 6: 白话文案

- [x] signalDisplay / StructuralAlerts / Onboarding / README / PWA manifest

### Task 7: 清理与回归

- [x] 删除 OpportunitiesPage、SignalsPage、AnalysisPage
- [x] build + pytest 192 passed
