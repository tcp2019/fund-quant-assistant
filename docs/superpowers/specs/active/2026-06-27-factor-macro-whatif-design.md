# v1.9 风格因子+宏观感知+模拟调仓 设计规格

> **Status:** active
> **Created:** 2026-06-27
> **Supersedes:** (none)
> **Superseded by:** (none)

## 目标

新增持仓风格暴露分析、宏观环境感知、模拟调仓 what-if 功能。

## 范围

### 包含

**A. 风格因子暴露**
- 基于名称关键词+基金类型做规模/价值分类
- API `GET /api/analysis/style-exposure` 返回组合暴露占比
- 前端 AnalysisPage 新增风格暴露饼图

**B. 宏观环境感知**
- akshare 拉取 10Y 国债收益率 + Shibor
- 判断环境（tight/neutral/loose）
- API `GET /api/analysis/macro`
- 前端 AnalysisPage 顶部环境指示条

**C. 模拟调仓**
- 前端 WhatIfPanel：选择基金、金额，计算指标变化
- Before/After 对比卡片
- 嵌入 AnalysisPage

### 不包含

- 完整 Fama-French 回归
- 实时宏观数据推送
- 模拟调仓信号生成

## 架构

### A. 风格因子

`services/factor_style.py`:
```python
CLASSIFY_SIZE = {"中小盘","创业板","科创"}→small_cap, {"大盘","蓝筹","沪深300","上证50"}→large_cap
CLASSIFY_STYLE = {"价值","红利","低波"}→value, {"成长","创新","科技"}→growth

def classify_fund_style(name: str, fund_type: str) -> dict
def compute_portfolio_style(session) -> StyleExposureOut
```

### B. 宏观感知

`services/macro.py`:
- `fetch_macro_indicators()` → dict with bond_10y, shibor_overnight, environment
- 利率变动 vs 60日前判断趋势
- akshare: `ak.bond_china_yield()`, `ak.shibor_rate()`

### C. 模拟调仓

前端组件 `components/WhatIfPanel.tsx`:
- 复用现有 FundSearchCombobox 选基金
- Before/After 对比：大类配置、集中度、风格暴露

## 错误处理

- 宏观数据拉取失败 → 返回 "数据暂不可用"
- 风格分类未知 → 归入 "其他"
- 模拟调仓纯前端计算，不写入数据库

## 测试策略

- `test_factor_style.py` — 分类逻辑 + API
- `test_macro.py` — 指标获取 + 环境判断
- 前端 WhatIfPanel 手动验证

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-27 | tcp | 初始版本 |
