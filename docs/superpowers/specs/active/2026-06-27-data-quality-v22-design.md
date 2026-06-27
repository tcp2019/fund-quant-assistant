# v2.2 数据质量增强与信号展示优化 设计规格

> **Status:** active
> **Created:** 2026-06-27
> **Supersedes:** (none)
> **Superseded by:** (none)

## 目标

解决三个遗留的数据质量问题：支付宝导入的基金代码不可靠、高相关性信号详情为纯文本 blob、NAV 数据源偶发 NaN/Inf 导致同步中断。

## 范围

### 包含

1. **基金代码解析器** — 基于基金名称 + SequenceMatcher 从本地 catalog 反查标准代码
2. **信号原因结构化** — 高相关性信号从纯文本 detail 提取 paired_fund_code/name/correlation
3. **NAV 数据健壮性** — NaN/Inf 过滤 + acc_nav fallback
4. **支付宝解析器增强** — 新 tab-export 格式（header-row 按列名映射）
5. **组合快照合并增强** — (code, name) 去重 + 加权平均 cost_price
6. **宏观感知增强** — 多数据源 fallback 链
7. **前端信号展示优化** — 高相关性卡片式展示

### 不包含

- 基金代码模糊搜索 UI（手动匹配界面）
- LLM 辅助的基金名称消歧
- 生产级多数据源健康检查

## 架构

### 基金代码解析器

```
OCR 上传 → resolve_holdings_fund_codes()
            ├── imported_code_matches_name() → 代码可用，跳过
            └── best_catalog_match()
                 ├── score ≥ 0.72 → 高置信度替换
                 ├── score ≥ 0.65 → 替换 + 低置信度警告
                 └── score < 0.65 → 无法匹配警告
```

- `SequenceMatcher` 比较归一化后的基金名称
- 份额后缀 (A/B/C/D/E) 匹配额外加分
- 先用名称核心片段预筛选候选集，再精细打分

### 信号原因结构化

```
signals API → enrich_high_correlation_reasons()
               ├── 从 detail 文本正则提取 correlation 值
               ├── 从 detail 文本正则提取 paired_fund_code
               └── 按 paired_fund_code 反查 paired_fund_name
```

### NAV 数据流

```
fetch_nav_from_akshare / _fetch_nav_from_tushare
  → _safe_nav_value() 过滤 NaN/Inf
  → acc_nav fallback 到 nav (如果 acc_nav 无效)
  → sync_fund_nav() 用 _normalize_nav_row() 归一化
```

## 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 代码解析方式 | 名称匹配，非 LLM | 确定性、低成本、可离线 |
| 名称匹配算法 | SequenceMatcher + 规则 | 基金名称结构化程度高，规则+序列匹配足够 |
| 匹配置信度阈值 | 0.65/0.72 双阈值 | 0.72 以上静默替换，0.65-0.72 附带警告 |
| 去重 key | (code, name) | 支付宝同一基金不同份额(code可能相同，name不 同)需分别保留 |

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-27 | tcp | 初始版本 |
