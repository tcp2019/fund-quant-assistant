# v2.4 净值实时化 设计规格

> **Status:** active
> **Created:** 2026-06-27

## 目标

持仓盈亏不再停留在导入时刻的快照，而是用最新基金净值动态重算，让 Dashboard 展示"此刻"的组合状态。

## 核心公式

```
实时市值 = 持仓份额 × 最新单位净值
实时盈亏 = 实时市值 - 总成本（份额 × 成本价）
实时收益率 = 实时盈亏 / 总成本
```

## 范围

### 包含

1. **build_overview 增强** — 批量查询最新净值，计算实时市值/盈亏
2. **Schema 扩展** — HoldingOut / OverviewOut 新增 current_* 和 nav_date 字段
3. **Dashboard 展示** — 总资产卡片显示实时市值和盈亏
4. **HoldingsTable 增强** — 每行显示实时市值对照
5. **降级回退** — 无净值数据时回退到快照值

### 不包含

- 今日盈亏（需昨日净值对比）
- 净值异动预警
- 前端自动轮询刷新
- 实时推送

## 架构

```
sync (已有, scheduler) → FundNavHistory 增量更新
                              ↓
build_overview() → 查询最新净值 → 实时值计算
                              ↓
GET /api/portfolio/overview → current_total_value / current_total_profit / nav_date
                              ↓
Dashboard / HoldingsTable → 实时市值展示
```

## 数据流

已有两条路径互补：

1. `revalue_holdings()` (已有) — 定时任务，**修改** Holding 表中的 market_value/profit
2. `build_overview()` (增强) — 读取时计算，**不修改**快照数据，增量返回 current_* 字段

## 降级

| 场景 | 行为 |
|------|------|
| 无 NAV 数据 | current_value = snapshot market_value |
| 份额为 0 | current_value = 0 |
| 成本无法计算 | current_profit = 0 |

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-27 | tcp | 初始版本 |
