# v2.5 今日盈亏与净值异动 设计规格

> **Status:** active
> **Created:** 2026-06-27
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Parent spec:** [2026-06-27-nav-realtime-design.md](./2026-06-27-nav-realtime-design.md)

## 目标

在 v2.4 实时市值/盈亏基础上，增加**今日盈亏**（对比上一交易日净值）与**净值异动预警**，让用户打开 Dashboard 即可感知「今天组合变化多少、哪些基金净值异常」。

## 核心公式

```
今日盈亏(单只) = 持仓份额 × (最新净值 − 上一交易日净值)
今日盈亏(组合) = Σ 各持仓今日盈亏
日涨跌幅       = 最新净值 / 上一交易日净值 − 1
```

## 范围

### 包含

1. **build_overview 增强** — 批量查最新 + 上一交易日净值，计算 `daily_profit` / `daily_total_profit`
2. **净值异动检测** — 复用 sync 层 15% 阈值，在 overview 返回 `nav_anomalies[]`
3. **Schema 扩展** — HoldingOut / OverviewOut 新增 daily 字段；新增 `NavAnomalyOut`
4. **Dashboard** — 「今日盈亏」StatCard；有异动的基金横幅提示
5. **HoldingsTable** — 有数据时展示今日盈亏列
6. **Dashboard 自动刷新** — TanStack Query `refetchInterval` 5 分钟（仅总览页）

### 不包含

- WebSocket 实时推送
- 异动推送通知 / 邮件
- 基于盘中估值的「今日盈亏」（仍用 T+1 官方净值）
- 历史每日盈亏曲线

## 架构

```
FundNavHistory (每只 fund 最新 + 上一日)
        ↓
build_overview() → daily_profit / nav_change_pct / nav_anomalies
        ↓
GET /api/portfolio/overview
        ↓
Dashboard StatCard + NavAnomalyBanner + HoldingsTable
```

## 降级

| 场景 | 行为 |
|------|------|
| 仅 1 条净值 | `daily_profit = null`，不参与组合今日盈亏汇总 |
| 无净值 | 与 v2.4 相同，回退快照 |
| 份额为 0 | `daily_profit = null` |
| 上一日净值为 0 | 跳过涨跌幅与异动检测 |

## 测试策略

- 单元：`build_overview` 有两日净值 → daily 字段正确；仅一日 → null；15%+ 变动 → anomaly
- 回归：v2.4 `current_*` 测试保持通过

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-27 | tcp | 初始版本 |
