# v1.8 NAV 复权 + 业绩增强 + 定期报告 设计规格

> **Status:** active
> **Created:** 2026-06-27
> **Supersedes:** (none)
> **Superseded by:** (none)

## 目标

修复 NAV 收益率计算失真（统一用累计净值），增强业绩信号维度，新增定期报告导出。

## 范围

### 包含

**A. NAV 复权处理**
- `_aligned_nav_series` 增加 `use_acc_nav` 参数，默认取累计净值
- `compute_correlation` / `compute_risk` / `compute_and_cache_metrics` 统一用复权净值

**B. 增强业绩评估**
- 新增 4 个指标：滚动夏普、Calmar 比率、下行捕获率、信息比率
- 每个指标独立 reason rule，融入 `compute_performance_signals`

**C. 定期报告**
- 新增 `GET /api/report/weekly` 返回 Markdown 文本
- 前端增加"导出周报"按钮

### 不包含

- 风格因子分析
- 宏观环境感知
- 动态权重
- 模拟调仓

## 架构

### A. NAV 复权

在 `services/analysis.py` 的 `_aligned_nav_series` 中：
- 新增参数 `use_acc_nav: bool = True`
- 当 `use_acc_nav=True`，从 `FundNavHistory.acc_nav` 取值而非 `nav`
- 调用方（`compute_correlation`, `compute_risk`）默认 true

在 `services/metrics_cache.py`：
- `compute_and_cache_metrics` 内部改用 `acc_nav` 序列计算指标

### B. 业绩增强

新文件 `services/signals/performance_metrics.py`：
```python
def rolling_sharpe(returns, window=60) -> float
def calmar_ratio(nav_series) -> float
def downside_capture(fund_returns, benchmark_returns) -> float
def info_ratio(fund_returns, benchmark_returns) -> float
```

在 `performance.py` 的 `compute_performance_signals` 中：
- 对每只基金计算 4 个新指标
- 新增 4 个 rule：`low_rolling_sharpe`, `low_calmar`, `high_downside_capture`, `low_info_ratio`
- 每个指标独立计分（正负双向），与 `underperform_peer` 叠加

### C. 定期报告

新增路由 `routes/report.py`：
```
GET /api/report/weekly?snapshot_id=<id> → text/markdown
```

报告通过模板拼接生成，数据来自现有 `build_overview`, `list_signals`, `compute_risk`, `rank_hot_themes`。

前端 Dashboard 页新增"导出周报"按钮，调用 API 下载 `.md` 文件。

## 错误处理

- NAV 复权：某只基金无 acc_nav 数据时回退到 nav
- 业绩指标：benchmark 数据缺失时跳过 `downside_capture` 和 `info_ratio`
- 报告生成：无快照时返回空模板

## 测试策略

- `test_nav_acc_usage.py` — 验证 acc_nav 被正确使用
- `test_performance_metrics.py` — 4 个指标函数单元测试
- `test_performance_enhanced.py` — 新 rule 融入信号引擎
- `test_report_weekly.py` — API 返回合法 Markdown

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-27 | tcp | 初始版本 |
