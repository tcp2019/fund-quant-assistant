# v1.2 候选推荐 + 基金搜索 + 浏览器通知 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

> **Status:** completed
> **Created:** 2026-06-21
> **Spec:** docs/superpowers/specs/active/2026-06-21-v12-recommendations-notifications-design.md
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Based on:** docs/superpowers/plans/completed/2026-06-21-v11-dashboard-import-pipeline.md

**Goal:** 交付 v1.2：增配信号展示 akshare 真实排行候选、导入基金搜索、sync 后强信号浏览器通知；生产环境零 mock/seed 数据。

**Architecture:** catalog/rank 两层 akshare 缓存表；metrics 在 sync 时从 FundNavHistory 计算；signals API 聚合 candidates；通知纯前端绑定真实 API 响应。

**Tech Stack:** Python 3.11, FastAPI, SQLModel, akshare, pytest | React 18, TypeScript, Notification API

---

## 文件结构（本批次）

```
backend/
├── app/db/models.py                          # + FundCatalog, FundRankCache
├── app/schemas/funds.py                      # search/candidate schemas
├── app/schemas/signals.py                    # + candidates on SignalOut
├── app/services/fund_catalog.py              # fund_name_em 刷新与搜索
├── app/services/fund_rankings.py             # akshare 排行拉取与缓存
├── app/services/fund_recommendations.py      # category → top N candidates
├── app/services/metrics_cache.py             # NAV → FundMetricsCache
├── app/services/data_sync.py                 # 调用 metrics_cache
├── app/api/routes/funds.py                   # search + catalog/refresh
├── app/api/routes/signals.py                 # attach candidates
├── app/main.py                               # register funds router
├── tests/fixtures/akshare/                   # 录制的真实响应 JSON
├── tests/test_fund_catalog.py
├── tests/test_fund_recommendations.py
├── tests/test_metrics_cache.py
└── tests/test_api_funds.py

frontend/
├── src/types/index.ts
├── src/api/client.ts
├── src/utils/notifications.ts
├── src/components/SignalsTable.tsx
├── src/components/FundSearchCombobox.tsx
├── src/pages/ImportPage.tsx
└── src/pages/SettingsPage.tsx
```

---

## M0：Sync 时写入 FundMetricsCache

### Task 1: metrics_cache 服务

**Files:**
- Create: `backend/app/services/metrics_cache.py`
- Test: `backend/tests/test_metrics_cache.py`

- [x] **Step 1: failing test — 给定 NAV 序列写入 sharpe/max_dd/1y return**

```python
def test_compute_and_cache_metrics(session, nav_rows):
    result = compute_and_cache_metrics(session, "110011")
    cache = session.exec(select(FundMetricsCache).where(...)).first()
    assert cache.sharpe_1y is not None
    assert cache.computed_from == "nav_history"
```

- [x] **Step 2: 实现 — 读 FundNavHistory 近 252 交易日，调用 metrics.py**
- [x] **Step 3: FundMetricsCache 模型增加 `computed_from: str` 字段（migration via create_all）**
- [x] **Step 4: PASS**

### Task 2: 接入 data_sync

**Files:**
- Modify: `backend/app/services/data_sync.py`
- Test: `backend/tests/test_data_sync.py`

- [x] **Step 1: sync_portfolio_funds 每只成功后调用 compute_and_cache_metrics**
- [x] **Step 2: 扩展 test — mock NAV 后 assert cache 行存在**
- [x] **Step 3: PASS**

---

## M1：基金目录 + 搜索

### Task 3: FundCatalog 模型与服务

**Files:**
- Modify: `backend/app/db/models.py`
- Create: `backend/app/services/fund_catalog.py`
- Create: `backend/tests/fixtures/akshare/fund_name_em_sample.json`
- Test: `backend/tests/test_fund_catalog.py`

- [x] **Step 1: FundCatalog 表 + refresh_catalog(session) 调 fund_name_em**
- [x] **Step 2: search_catalog(session, q, limit) 模糊匹配**
- [x] **Step 3: TTL 7 天 — stale 时 refresh**
- [x] **Step 4: test 用 fixture JSON（真实录制结构）mock akshare**

### Task 4: Funds API

**Files:**
- Create: `backend/app/schemas/funds.py`
- Create: `backend/app/api/routes/funds.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api_funds.py`

- [x] **Step 1: GET /api/funds/search?q=&limit=8**
- [x] **Step 2: POST /api/funds/catalog/refresh**
- [x] **Step 3: catalog 空且 refresh 失败 → 503**
- [x] **Step 4: API tests PASS**

### Task 5: Import 搜索补代码

**Files:**
- Create: `frontend/src/components/FundSearchCombobox.tsx`
- Modify: `frontend/src/pages/ImportPage.tsx`
- Modify: `frontend/src/api/client.ts`, `frontend/src/types/index.ts`

- [x] **Step 1: fund_code 为空时显示搜索框**
- [x] **Step 2: 选中结果回填 code + name**
- [x] **Step 3: 手动验证**

---

## M2：候选推荐

### Task 6: 排行缓存与拉取

**Files:**
- Modify: `backend/app/db/models.py`
- Create: `backend/app/services/fund_rankings.py`
- Create: `backend/tests/fixtures/akshare/fund_open_fund_rank_em_sample.json`
- Create: `backend/tests/fixtures/akshare/fund_money_rank_em_sample.json`
- Test: `backend/tests/test_fund_rankings.py`

- [x] **Step 1: FundRankCache 表**
- [x] **Step 2: fetch_rankings(category) — 映射到 open/money rank API**
- [x] **Step 3: 24h TTL；失败抛错，不返回假数据**
- [x] **Step 4: 过滤 NaN 近1年、排除 exclude_codes**

### Task 7: recommend 服务

**Files:**
- Create: `backend/app/services/fund_recommendations.py`
- Test: `backend/tests/test_fund_recommendations.py`

- [x] **Step 1: recommend_funds(session, category, exclude_codes, limit=3)**
- [x] **Step 2: 返回 FundCandidateOut 含 data_source + as_of_date**
- [x] **Step 3: bond/qdii/gold 过滤单测**

### Task 8: Signals API + UI

**Files:**
- Modify: `backend/app/schemas/signals.py`, `backend/app/api/routes/signals.py`
- Modify: `frontend/src/components/SignalsTable.tsx`, `frontend/src/types/index.ts`

- [x] **Step 1: SignalOut.candidates 字段**
- [x] **Step 2: list_signals 对 fund_code="" add 信号调用 recommend**
- [x] **Step 3: SignalsTable 候选列表（大类增配展开）+ 合规 disclaimer**
- [x] **Step 4: akshare 失败时候选为空 + 空态文案**

---

## M3：浏览器通知

### Task 9: 通知工具与 Settings

**Files:**
- Create: `frontend/src/utils/notifications.ts`
- Modify: `frontend/src/pages/SettingsPage.tsx`

- [x] **Step 1: get/set notificationsEnabled in localStorage**
- [x] **Step 2: requestPermission + 测试通知按钮**
- [x] **Step 3: Settings UI 区块**

### Task 10: Sync 后触发

**Files:**
- Modify: `frontend/src/pages/ImportPage.tsx`
- Modify: `frontend/src/pages/SignalsPage.tsx`
- Modify: `frontend/src/pages/SettingsPage.tsx`

- [x] **Step 1: maybeNotifyStrongSignals(snapshotId, signals)**
- [x] **Step 2: strength>=4 add/reduce 才通知；snapshot 去重**
- [x] **Step 3: sync 失败不通知**

---

## M4：验收

### Task 11: 全量验证与文档

- [x] **Step 1: `pytest backend/tests -v` 全绿**
- [x] **Step 2: `npm run build` 通过**
- [x] **Step 3: 手动：Settings 刷新 catalog → Import 搜索 → sync → 信号页见候选**
- [x] **Step 4: plan → completed/；更新主 spec 演进路径与 README 索引**

---

## Spec 覆盖自检

| Spec 需求 | Task |
|-----------|------|
| 真实数据红线 | 6–8（无 seed） |
| FundMetricsCache | 1–2 |
| 基金搜索 | 3–5 |
| 候选推荐 | 6–8 |
| 浏览器通知 | 9–10 |
| 错误空态 | 4, 8 |

---

## 执行顺序

严格 M0 → M1 → M2 → M3 → M4。M0 完成后业绩信号可用真实 metrics；M1 可独立验收搜索；M2 依赖 M0 catalog/rank；M3 最后。
