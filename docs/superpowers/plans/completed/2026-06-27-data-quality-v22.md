# v2.2 数据质量增强与信号展示优化 Implementation Plan

> **Status:** completed
> **Created:** 2026-06-27
> **Spec:** docs/superpowers/specs/active/2026-06-27-data-quality-v22-design.md
> **Supersedes:** (none)
> **Superseded by:** (none)

**Goal:** 解决支付宝导入基金代码不可靠、高相关性信号纯文本 blob、NAV 数据 NaN/Inf 三大数据质量问题。

**Architecture:** 新增 fund_code_resolver 用名称反查标准代码；新增 reason_enrichment 从 detail 文本提取结构化字段；data_sync 全链路 NaN/Inf 过滤。

**Tech Stack:** Python 3.13+ / FastAPI / SQLModel / difflib, TypeScript / React 19 / Tailwind CSS

---

### Task 1: 基金代码解析器

**Files:**
- Create: `backend/app/services/fund_code_resolver.py`
- Create: `backend/tests/test_fund_code_resolver.py`
- Modify: `backend/app/api/routes/ocr.py`

- [x] **Step 1: 实现名称匹配核心** — `score_fund_name()`, `best_catalog_match()`, `imported_code_matches_name()`
- [x] **Step 2: 实现批量解析** — `resolve_holdings_fund_codes()`, `fix_snapshot_holdings_codes()`
- [x] **Step 3: 集成到 OCR 上传流程** — `_build_upload_response()` 调用 `resolve_holdings_fund_codes()`
- [x] **Step 4: 编写测试** — mock catalog + 模糊名称匹配 + 错误代码替换场景

### Task 2: 信号原因结构化

**Files:**
- Create: `backend/app/services/signals/reason_enrichment.py`
- Create: `backend/tests/test_reason_enrichment.py`
- Modify: `backend/app/api/routes/signals.py`
- Modify: `backend/app/schemas/signals.py`

- [x] **Step 1: 实现提取逻辑** — `enrich_high_correlation_reasons()` 从 detail 文本正则提取 correlation/paired_code
- [x] **Step 2: 扩展 SignalReason schema** — 新增 `paired_fund_code`, `paired_fund_name`, `correlation`
- [x] **Step 3: 集成到 signals API** — `list_signals()` 调用 enrichment
- [x] **Step 4: 编写测试**

### Task 3: 信号引擎增强

**Files:**
- Modify: `backend/app/services/signals/engine.py`

- [x] **Step 1: 高相关性信号输出结构化字段** — `paired_fund_code`, `paired_fund_name`, `correlation`

### Task 4: NAV 数据健壮性

**Files:**
- Modify: `backend/app/services/data_sync.py`
- Modify: `backend/tests/test_data_sync.py`

- [x] **Step 1: 实现安全转换** — `_safe_nav_value()`, `_normalize_nav_row()`
- [x] **Step 2: 全链路应用** — akshare + tushare 路径均归一化
- [x] **Step 3: 事务安全** — 各阶段异常后 `session.rollback()`
- [x] **Step 4: 编写 NaN fallback 测试**

### Task 5: 支付宝解析器增强

**Files:**
- Modify: `backend/app/services/ocr/parsers/alipay.py`
- Create: `backend/tests/fixtures/ocr/alipay_tab_code_first_sample.txt`
- Modify: `backend/tests/test_ocr_parsers.py`
- Modify: `backend/tests/test_api_ocr.py`

- [x] **Step 1: header-row 解析** — `_tab_header_columns()` 按列名映射字段
- [x] **Step 2: (code, name) 去重** — 替代旧 code-only 去重
- [x] **Step 3: 利润推算** — `_profit_rate_from_amounts()`
- [x] **Step 4: 新格式集成测试**

### Task 6: 组合快照合并增强

**Files:**
- Modify: `backend/app/repositories/portfolio.py`

- [x] **Step 1: 加权平均合并** — `_merge_holding()` 计算合并后 cost_price/profit_rate
- [x] **Step 2: (code, name) 去重** — 替代旧 code-only 去重

### Task 7: 宏观感知增强

**Files:**
- Modify: `backend/app/services/macro.py`
- Modify: `backend/tests/test_macro.py`

- [x] **Step 1: 收益率趋势** — `_bond_trend()` rising/falling/stable
- [x] **Step 2: 多数据源 fallback** — bond_zh_us_rate → bond_china_yield → 曲线筛选
- [x] **Step 3: Shibor fallback** — macro_china_shibor_all → shibor_rate → 默认 1.5

### Task 8: 前端信号展示优化

**Files:**
- Modify: `frontend/src/components/SignalsTable.tsx`
- Modify: `frontend/src/utils/signalDisplay.ts`
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/components/HotThemeRadar.tsx`
- Modify: `frontend/src/pages/ImportPage.tsx`

- [x] **Step 1: 结构化展示高相关性** — Reasons split + 配对基金卡片 + 相关系数
- [x] **Step 2: 工具函数** — `formatFundLabel()`, `resolveCorrelationPair()`
- [x] **Step 3: 类型扩展** — SignalReason 新增字段
- [x] **Step 4: 附带修复** — HotThemeRadar 动态颜色、ImportPage 错误 banner、confirmOcr 错误处理
