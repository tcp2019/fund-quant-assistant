# 支付宝 OCR 多格式解析 + 前端盈亏展示 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

> **Status:** completed
> **Created:** 2026-06-21
> **Spec:** docs/superpowers/specs/active/2026-06-21-fund-quant-assistant-design.md
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Based on:** docs/superpowers/plans/completed/2026-06-21-fund-quant-assistant.md

**Goal:** 提升支付宝持仓导入成功率：支持列表占比、合并行、Tab 导出等真实 OCR 文本格式；放宽缺份额/代码时的校验；统一前端 A 股盈亏配色与格式化。

**Architecture:** `parse_alipay_text` 按内容特征链式尝试子 parser（Tab → merged → detail → list）；`base.py` 抽取金额/名称工具；`validate_holding` 区分「警告」与「阻断」；前端 `utils/format` + `utils/profitLoss` 去重复。

**Tech Stack:** Python 3.11, pytest | React 18, TypeScript, Tailwind

---

## 文件变更摘要

```
backend/app/services/ocr/parsers/base.py      # MONEY 正则、parse_money、strip_fund_name、extract_fund_code 增强
backend/app/services/ocr/parsers/alipay.py    # 四种子 parser + 自动路由
backend/app/services/ocr/pipeline.py          # validate_holding 放宽
backend/tests/fixtures/ocr/
  alipay_list_sample.txt                      # 列表占比 OCR 样本（30+ 只）
  alipay_merged_sample.txt                    # 合并行导出
  alipay_tab_export_sample.txt                # Tab 分隔导出
backend/tests/test_ocr_parsers.py             # 4 个新测试
frontend/src/utils/format.ts                  # 金额/百分比格式化
frontend/src/utils/profitLoss.ts              # A 股红涨绿跌 class
frontend/src/components/HoldingsTable.tsx     # 使用 utils
frontend/src/components/StatCard.tsx
frontend/src/pages/Dashboard.tsx
frontend/src/pages/HoldingsPage.tsx
frontend/src/pages/ImportPage.tsx               # 零条解析错误提示
```

---

### Task 1: Base parser 工具

**Files:**
- Modify: `backend/app/services/ocr/parsers/base.py`
- Test: `backend/tests/test_ocr_parsers.py`

- [x] **Step 1: 添加 `MONEY` 正则与 `parse_money`**
- [x] **Step 2: 添加 `strip_fund_name` 去除 OCR 标签噪声**
- [x] **Step 3: `extract_fund_code` 忽略金额尾部（如 `6,217730.00`）**
- [x] **Step 4: 测试 `test_extract_fund_code_ignores_amount_tail`**

---

### Task 2: 支付宝 Tab 导出 parser

**Files:**
- Modify: `backend/app/services/ocr/parsers/alipay.py`
- Create: `backend/tests/fixtures/ocr/alipay_tab_export_sample.txt`
- Test: `backend/tests/test_ocr_parsers.py`

- [x] **Step 1: `_parse_alipay_tab_export` — `\t` 分隔，序号/名称/代码/市值/收益率**
- [x] **Step 2: 跳过余额宝、保险等非基金行**
- [x] **Step 3: 由收益率反推 profit 与 implied cost**
- [x] **Step 4: `test_parse_alipay_tab_export_with_spaces_and_category`**

---

### Task 3: 支付宝合并行导出 parser

**Files:**
- Modify: `backend/app/services/ocr/parsers/alipay.py`
- Create: `backend/tests/fixtures/ocr/alipay_merged_sample.txt`

- [x] **Step 1: `_parse_alipay_merged_text` — `名称 012422 42036.78 +90.70%`**
- [x] **Step 2: `test_parse_alipay_merged_export`**

---

### Task 4: 支付宝列表占比 parser

**Files:**
- Modify: `backend/app/services/ocr/parsers/alipay.py`
- Create: `backend/tests/fixtures/ocr/alipay_list_sample.txt`

- [x] **Step 1: `_normalize_list_text` — 单行 OCR 归一化（千分位、占比、字段分隔）**
- [x] **Step 2: `_parse_alipay_list_text` — 名称/市值/持有收益/收益率/占比**
- [x] **Step 3: 原详情块逻辑迁至 `_parse_alipay_detail_text`**
- [x] **Step 4: `parse_alipay_text` 链式路由（Tab → merged → detail → list）**
- [x] **Step 5: `test_parse_alipay_list_view` — 断言 ≥30 条且首条字段正确**

---

### Task 5: 校验与导入体验

**Files:**
- Modify: `backend/app/services/ocr/pipeline.py`
- Modify: `frontend/src/pages/ImportPage.tsx`

- [x] **Step 1: `validate_holding` — 仅市值 ≤0 为硬错误；缺代码/份额为警告**
- [x] **Step 2: 有份额时才做市值/份额/成本价偏差检查**
- [x] **Step 3: ImportPage 解析 0 条时显示明确错误文案**

---

### Task 6: 前端格式化与 A 股配色

**Files:**
- Create: `frontend/src/utils/format.ts`
- Create: `frontend/src/utils/profitLoss.ts`
- Modify: `HoldingsTable.tsx`, `StatCard.tsx`, `Dashboard.tsx`, `HoldingsPage.tsx`

- [x] **Step 1: `formatProfitAmount` — 金额不带符号，靠颜色表方向**
- [x] **Step 2: `formatSignedPercent` — 正数带 `+`**
- [x] **Step 3: `profitLossTextClass` / `profitLossToneClass` — 涨红跌绿**
- [x] **Step 4: Dashboard / HoldingsTable / StatCard / HoldingsPage 接入**

---

### Task 7: 验收

- [x] **Step 1: `pytest backend/tests/test_ocr_parsers.py -v` 全绿**
- [x] **Step 2: 手动粘贴 `alipay_list_sample.txt` → 导入页应解析 30+ 条**
- [x] **Step 3: 更新 spec Changelog 与本 plan**

---

## Spec 覆盖自检

| Spec 需求（v1.0.1） | 对应 Task |
|---------------------|-----------|
| 支付宝多格式 OCR | Task 2–4 |
| 缺份额/代码可导入 | Task 5 |
| OCR 零条解析提示 | Task 5 |
| A 股盈亏配色 | Task 6 |
| Fixture 回归 | Task 2–4 |
