# v1.5 组合管理基础（A/B/C/D）设计规格

> **Status:** active
> **Created:** 2026-06-22
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Parent spec:** [2026-06-21-fund-quant-assistant-design.md](./2026-06-21-fund-quant-assistant-design.md)
> **Builds on:** [v1.3 类内增配](./2026-06-22-intra-category-rebalance-allocation-design.md) · [v1.4 机会中心](./2026-06-22-opportunities-hotspot-radar-design.md)

## 目标

在 v1.3 增配分配与 v1.4 机会中心之上，交付 **完整双向再平衡、风险去重、业绩层专业化、规则回测校验** 四条工作流，使系统从「分析 + 单向增配建议」升级为 **可执行的组合管理流程**。

## 范围

### A — 双向再平衡

| 项 | 说明 |
|----|------|
| A1 类内减配分配 | 大类超配时，按类内 **超配市值** 比例分配负 `suggested_amount`（对称 v1.3） |
| A2 最小交易额 | `min_suggested_trade_cny`（默认 ¥500）；\|amount\| 低于阈值 → 0，不进机会中心行动清单 |
| A3 强制再平衡审视 | 距最新快照 ≥ `rebalance_force_days` 时，有效带宽降为 0（任意偏离触发）→ **v1.6 改为审视提醒，见 [signal-coherence spec](./2026-06-22-signal-coherence-structural-first-design.md)** |
| A4 类内 custom 权重 UI | Settings 表格编辑 `fund_target_weights`（需拉持仓列表） |

### B — 风险与去重

| 项 | 说明 |
|----|------|
| B1 相关性接入信号引擎 | `run_signal_engine` 使用与 Analysis 相同的 90 日相关矩阵 |
| B2 Consolidation 层 | 同大类持仓 > `max_funds_per_category`（默认 10）→ 大类级 `watch` |
| B3 高相关 cluster 提示 | 在 Consolidation reason 中汇总高相关对数量 |

### C — 业绩层专业化

| 项 | 说明 |
|----|------|
| C1 分资产类别阈值 | 股/债/货/QDII/其他 使用不同 Sharpe、最大回撤阈值 |
| C2 增配 veto 延伸 | `performance_blocked_add` 不进 `add_holding` 行动；score 排序降权 |
| C3 探索候选排序 | `explore_balanced`：0.7×近1年 + 0.3×近1月，缺数据排后 |
| C4 UI 文案分区 | 机会页 explore / 热点标注「浏览参考，非配置建议」 |

### D — 回测与校验

| 项 | 说明 |
|----|------|
| D1 带宽敏感性 | `GET /api/backtest/sensitivity`：3/5/8/10% 带宽下触发大类数 |
| D2 快照信号统计 | 各历史快照上再平衡触发次数（只读回放，不写 SignalRecord） |
| D3 文档 | 主 spec 演进表 + DEFAULT 阈值附说明 |

### 不包含

- 自动下单、券商对接
- 风险平价 / 均值方差优化
- 完整 PnL 回测（Future）
- LLM 解释层

## A1 类内减配算法

与 v1.3 对称：

1. `surplus_i = max(0, market_value_i - target_mv_i)`
2. `suggested_amount_i = -round(category_reduce_amount × surplus_i / Σ surplus, 2)`（末只消差）
3. 业绩层 **不阻止** 减配；弱业绩基金在减配分配中获得更高权重（`performance_prioritized_reduce`，v1.5.1）
4. 限购规则对减配沿用现有逻辑

## A2 / A3 阈值

```json
{
  "rebalance_deviation_pct": 5.0,
  "rebalance_force_days": 365,
  "single_fund_max_pct": 25.0,
  "correlation_max": 0.85,
  "min_suggested_trade_cny": 500.0,
  "max_funds_per_category": 10
}
```

强制审视（v1.5，v1.6 已变更）：`days_since_snapshot >= rebalance_force_days` → `effective_threshold = 0`。v1.6 移除 threshold=0，改为带宽内 `rebalance_review_due` 提醒信号。

## B2 Consolidation

- 输入：大类 → 基金列表
- 若 `len(codes) > max_funds_per_category`：输出大类级 `watch`，`fund_code=""`，rule=`category_overcrowded`
- 与集中度层独立；score 贡献为 concentration 权重 × watch

## C1 分资产阈值

| category | sharpe_weak | max_dd_bad |
|----------|-------------|------------|
| stock | 0.5 | -20% |
| bond | 0.3 | -10% |
| money | 0.0 | -1% |
| qdii | 0.4 | -25% |
| other | 0.5 | -20% |

超额收益、同类排名规则不变。

## D API

```
GET /api/backtest/sensitivity
→ { snapshot_id, total_value, scenarios: [{ threshold_pct, triggered_categories, signals }] }

GET /api/backtest/snapshot-stats
→ { snapshots: [{ snapshot_id, created_at, rebalance_triggers, category_count_max }] }
```

## 架构数据流

```
holdings + strategy + metrics + correlation matrix
        ↓
compute_rebalance_signals (force_days aware)
        ↓
intra_category: add amounts + reduce amounts
        ↓
concentration (+ correlation pairs) + consolidation
        ↓
performance (category-aware)
        ↓
aggregate_signals → apply_min_trade → apply_purchase_limits
        ↓
opportunities (performance_blocked excluded from buy)
```

## 错误处理

| 场景 | 行为 |
|------|------|
| 减配侧全 surplus=0 | 单只金额 0，大类减配信号保留 |
| 无 NAV 无法算相关 | 跳过相关对，Consolidation 仍生效 |
| 无历史快照 | backtest 返回空列表 |
| custom 权重和 ≠ 1 | PUT strategy 422（已有） |

## 测试策略

- 单元：减配分配、min_trade、force_days、consolidation、category performance、explore sort、backtest sensitivity
- 集成：`run_signal_engine` 含相关矩阵；opportunities 不含 blocked buy
- API：backtest 端点 happy path

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-22 | Agent + User | 初始版本；A/B/C/D 四工作流合并为 v1.5 |
| 2026-06-22 | Agent | 已交付：减配分配、min_trade、force_review、相关性、Consolidation、分资产业绩、回测 API、Settings/机会 UI |
| 2026-06-22 | Agent | v1.5.1：减配业绩优先权重；Analysis 回测面板；snapshot-stats 用用户策略 |
