# v1.5 组合管理基础（A/B/C/D）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** completed
> **Created:** 2026-06-22
> **Spec:** docs/superpowers/specs/active/2026-06-22-portfolio-management-foundation-design.md
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Based on:** v1.3 类内增配 · v1.4 机会中心

**Goal:** 交付双向再平衡、相关性/去重、分资产业绩阈值、回测校验四条工作流，使信号与机会中心可双向执行。

**Architecture:** 扩展 `intra_category` 减配对称算法；`engine` 接入 `compute_correlation`、Consolidation、min_trade；`performance` 分 category 阈值；`backtest/sensitivity` 提供带宽敏感性 API；Settings/机会页 UI 同步。

**Tech Stack:** Python 3.11, FastAPI, SQLModel, pytest | React, TypeScript, Tailwind

---

## 交付清单

### A — 双向再平衡
- [x] `allocate_category_reduce` / `compute_fund_surpluses`
- [x] `engine._build_category_reduce_amounts` + 大类减配行
- [x] `min_trade.apply_min_trade_to_signals`
- [x] `rebalance.force_review` + Settings `min_suggested_trade_cny`
- [x] Settings 类内 custom 权重表格

### B — 风险与去重
- [x] `run_signal_engine` 接入 `compute_correlation`
- [x] `consolidation.compute_consolidation_signals` + `append_consolidation_signals`
- [x] Settings `max_funds_per_category`

### C — 业绩专业化
- [x] `performance.CATEGORY_THRESHOLDS`
- [x] `action_classifier` performance_blocked → watch
- [x] `fund_rankings.explore_balanced` + opportunities 探索排序
- [x] 机会页 explore 文案分区

### D — 回测
- [x] `GET /api/backtest/sensitivity`
- [x] `GET /api/backtest/snapshot-stats`
- [x] 单元/API 测试

### 验证
- [x] `pytest tests -v` — 109 passed
