# v1.3 类内目标权重增配分配 设计规格

> **Status:** active
> **Created:** 2026-06-22
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Parent spec:** [2026-06-21-fund-quant-assistant-design.md](./2026-06-21-fund-quant-assistant-design.md)

## 目标

将大类再平衡缺口（如股票型低配 ¥52,806）从 **「同类均摊」** 改为 **「按类内目标权重缺口分配」**，对齐行业主流的 model-portfolio 再平衡逻辑；并用业绩层作 **过滤**（业绩差的基金不分配增配金额）。消除信号页 30+ 条相同得分/金额的行，使每条 `suggested_amount` 可执行、可解释。

## 背景

当前实现（v1.2.1）在 `aggregate_signals` 中：

```python
suggested_amount += abs(rebalance_signal["suggested_amount"]) / share  # share = 类别内基金只数
```

导致同一低配大类下所有持仓得分、建议金额、原因摘要相同。大类缺口本身由目标权重反算是正确的；缺失的是 **类内每只基金的目标权重** 与 **缺口分配算法**。

用户确认方向：**目标权重缺口分配为主 + 业绩差的不分配为过滤**。

## 范围

### 包含（v1.3）

1. **类内目标权重** 推导与（可选）用户配置
2. **增配金额分配算法**：按类内缺口比例分配大类 `suggested_amount`
3. **业绩过滤**：业绩层 `reduce` / 强 `watch` 的基金 `suggested_amount = 0`（仍保留 score/reasons）
4. **信号引擎** `aggregate_signals` 重构 + 单元测试
5. **原因文案**：单只基金 detail 区分「类内缺口 ¥X」与「大类总缺口 ¥Y」
6. **文档**：主 spec 更新 suggested_amount 行为

### 不包含

- 全新 UI 页面编辑每只基金目标权重（v1.3 仅 API/Settings 可扩展位，UI 可 v1.3.1）
- 风险平价 / 均值方差优化
- 自动下单
- 减仓金额的类内分配（v1.3 聚焦增配；减仓仍以大类 + 集中度层为主）

## 类内目标权重

### 定义

对大类 `C`（如 `stock`），设大类目标权重 `T_C`（来自现有 `strategy_config.target_weights_json`）。

每只基金 `i ∈ C` 的 **组合目标权重**：

```
target_weight_i = T_C × w_i
```

其中 `w_i` 为 **类内目标权重**，Σ w_i = 1（仅对该大类持仓求和）。

### 默认推导模式（`intra_category_mode`）

| 模式 | 说明 | 默认 |
|------|------|------|
| `equal` | 类内等权：`w_i = 1 / n` | **是** |
| `pro_rata` | 按当前类内市值占比：`w_i = mv_i / Σ mv` | |
| `custom` | 用户配置 `fund_target_weights_json` | |

存储：在 `strategy_config` 增加字段（SQLite migration via session alter）：

```json
{
  "intra_category_mode": "equal",
  "fund_target_weights_json": { "110011": 0.15, "007491": 0.10 }
}
```

- `custom` 时：`fund_target_weights_json` 键为 `fund_code`，值为 **类内权重**（同大类内之和应为 1.0，容差 ±0.01）
- 未出现在 custom 中的持仓：mode 回退为 `equal` 在剩余基金间重新归一

### 为何默认 `equal`

- 用户未配置模型组合时，等权是行业常见的 **neutral prior**
- 比「按只数均分金额」更合理：等权目标下，**低于等权线的基金会分到更多缺口**
- `pro_rata` 适合「维持现有结构、只补大类」场景，Settings 可切换

## 增配分配算法

### 输入

- `category_gap_amount`：大类增配缺口金额（正数，来自 `compute_rebalance_signals`）
- 该大类下持仓列表 `holdings_in_C`，含 `fund_code`, `market_value`
- 类内目标权重 `w_i`
- 组合总市值 `total_value`

### 步骤

1. **计算每只基金组合目标市值**  
   `target_mv_i = T_C × w_i × total_value`

2. **计算类内缺口（仅增配方向）**  
   `gap_i = max(0, target_mv_i - market_value_i)`

3. **业绩过滤**  
   若基金业绩层信号为 `reduce`，或 `watch` 且含 `excess_return_1y` / `peer_return_percentile_3m` / `max_drawdown_1y` / `sharpe_1y` 规则 → `gap_i = 0`（可追加 reason `performance_blocked_add`）

4. **归一分配大类缺口**  
   `sum_gap = Σ gap_i`  
   - 若 `sum_gap == 0`：所有单只 `suggested_amount = 0`（大类信号仍保留整笔 + 候选）  
   - 否则：`suggested_amount_i = round(category_gap_amount × gap_i / sum_gap, 2)`  
   - 末只基金用「总额减已分配」消除四舍五入误差，保证 Σ = `category_gap_amount`（在过滤后子集上）

5. **申购限购**（现有 `apply_purchase_limits_to_signals`）在分配 **之后** 应用，逻辑不变

### 得分

- `score` 计算逻辑 **不变**（三层加权）；仅 `suggested_amount` 与 derive `signal_type` 的输入改变
- 弱增配（score 18.3 仅来自 rebalance）仍可能 `add`，但金额因缺口不同而分化

### 输出示例

大类股票型低配 9.1%，缺口 ¥52,806；31 只基金，等权目标 1/31 ≈ 3.23% 组合权重。

| 基金 | 当前占比 | 等权目标 | 类内缺口 | 分配金额 |
|------|----------|----------|----------|----------|
| A | 0.5% | 3.23% | 大 | ¥8,200 |
| B | 2.8% | 3.23% | 小 | ¥1,400 |
| C（业绩 reduce） | 1.0% | 3.23% | — | ¥0 |

原因摘要示例：  
`大类低配 · 股票型低配 9.1%，大类缺口 ¥52806；类内缺口 ¥8200（等权目标 3.2%）`

## 架构

### 数据流

```
strategy_config (T_C, intra_category_mode, fund_target_weights)
        +
holdings + fund_categories
        +
compute_rebalance_signals → category_gap_amount
        +
compute_intra_category_targets → w_i
        +
compute_performance_signals → filter mask
        ↓
allocate_category_add_amount → per-fund suggested_amount
        ↓
aggregate_signals (existing layers for score/reasons)
        ↓
apply_purchase_limits_to_signals
```

### 新增模块

```
backend/app/services/signals/intra_category.py
  - resolve_intra_category_weights(mode, holdings, custom_json) → dict[fund_code, float]
  - compute_fund_gaps(holdings, targets, total_value, T_C) → dict[fund_code, float]
  - allocate_category_add(gap_amount, fund_gaps, performance_mask) → dict[fund_code, float]
```

`engine.aggregate_signals` 调用上述函数，删除 `÷ share` 均摊逻辑。

### API / Settings（最小变更）

`StrategyOut` / `StrategyUpdateIn` 增加可选字段：

```python
intra_category_mode: Literal["equal", "pro_rata", "custom"] = "equal"
fund_target_weights: dict[str, float] | None = None  # custom 模式
```

Settings 页 v1.3 可仅暴露「类内分配：等权 / 按现占比」下拉；custom 权重表格留 v1.3.1。

## 错误处理

| 场景 | 行为 |
|------|------|
| 大类无持仓 | 不产生单只增配；仅大类信号 + 候选 |
| 过滤后无可分配基金 | 单只金额全 0；大类信号与候选仍展示 |
| custom 权重和 ≠ 1 | PUT strategy 422 |
| 某基金无 metrics | 不过滤，仍参与分配（缺数据不惩罚） |
| category_gap ≤ 0 | 不进入增配分配 |

## 测试策略

| 用例 | 断言 |
|------|------|
| 等权目标，3 只同类别、市值不同 | 分配金额不同，总和 = 大类缺口 |
| 业绩 reduce 基金 | suggested_amount = 0 |
| 全被过滤 | 单只全 0，大类信号保留 |
| 替换现有 `test_aggregate_signals_weak_rebalance_add` | 不再断言均分相等 |
| 限购 cap | 在分配后仍正确降级 |

## 与现有 UI 的关系

- **不必**合并 31 行为 1 行；金额分化后表格自然可读
- 可选 v1.3.1：增配 tab 默认按 `suggested_amount` 降序
- 大类行（`fund_code=""`）继续展示总缺口 + akshare 候选

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-22 | Agent + User | 初始版本；确认 equal 默认 + 业绩过滤 + 目标缺口分配 |
| 2026-06-22 | Agent | 已交付：intra_category 模块、Settings API/UI、aggregate_signals 重构 |
