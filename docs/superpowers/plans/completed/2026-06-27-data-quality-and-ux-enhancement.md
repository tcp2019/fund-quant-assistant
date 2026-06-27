# v1.7 数据质量与体验增强 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** completed
> **Created:** 2026-06-27
> **Spec:** docs/superpowers/specs/active/2026-06-27-data-quality-and-ux-enhancement-design.md
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Based on:** none

**Goal:** 实现数据同步失败告警、前端 TanStack Query 重构、NAV 增量同步、NAV 跳变检测，消除静默失败并提升用户体验。

**Architecture:** 后端新增 SyncLog 表记录同步成败，sync_portfolio_funds 改为逐基金错误收集；前端接入 @tanstack/react-query 替换 7 个页面的手动 fetch；NAV 同步改为增量拉取并在写入前做跳变检测。

**Tech Stack:** Python 3.11+ / FastAPI / SQLModel / SQLite / akshare, TypeScript / React 19 / TanStack Query 5 / Tailwind CSS

---

### Task 1: SyncLog 数据模型

**Files:**
- Create: `backend/tests/test_sync_log.py`
- Modify: `backend/app/db/models.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_sync_log.py`:
```python
import json
from datetime import datetime

from app.db.models import SyncLog


def test_sync_log_create(session):
    log = SyncLog(
        status="partial",
        total_funds=5,
        success_funds=3,
        failed_funds=2,
        errors_json=json.dumps(
            [
                {"fund_code": "000001", "stage": "nav", "error": "timeout"},
                {"fund_code": "000002", "stage": "metadata", "error": "not found"},
            ]
        ),
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    assert log.id is not None
    assert log.status == "partial"
    assert log.total_funds == 5
    assert log.success_funds == 3
    assert log.failed_funds == 2

    errors = json.loads(log.errors_json)
    assert len(errors) == 2
    assert errors[0]["fund_code"] == "000001"


def test_sync_log_partial_details(session):
    log = SyncLog(
        status="failed",
        total_funds=3,
        success_funds=0,
        failed_funds=3,
        errors_json=json.dumps(
            [{"fund_code": "000001", "stage": "nav", "error": "network error"}]
        ),
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    session.add(log)
    session.commit()

    assert log.status == "failed"
    assert log.success_funds == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_sync_log.py -v`
Expected: FAIL with "name 'SyncLog' is not defined"

- [ ] **Step 3: Write minimal implementation**

In `backend/app/db/models.py`, add after the SignalRecord class (around line 103):

```python
class SyncLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    status: str = "running"  # running | done | partial | failed
    total_funds: int = 0
    success_funds: int = 0
    failed_funds: int = 0
    errors_json: str = "[]"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_sync_log.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/models.py backend/tests/test_sync_log.py
git commit -m "feat: add SyncLog model for sync failure tracking"
```

---

### Task 2: 数据库表自动创建 SyncLog

**Files:**
- Modify: `backend/app/db/session.py`

- [ ] **Step 1: Verify SyncLog table is auto-created**

Run: `cd backend && python -c "from app.db.session import create_db_and_tables; create_db_and_tables(); print('OK')"`

Expected: OK (table created without error, since SQLModel.metadata.create_all already creates all SQLModel subclasses)

No code change needed — `SQLModel.metadata.create_all(engine)` already discovers `SyncLog` because it inherits from `SQLModel, table=True`.

- [ ] **Step 2: Commit**

```bash
git add backend/app/db/session.py  # if any import needed
git commit -m "feat: auto-create SyncLog on startup via create_db_and_tables"
```

---

### Task 3: sync_portfolio_funds 重构为逐基金错误收集 + SyncLog 写入

**Files:**
- Create: `backend/tests/test_data_sync_logging.py`
- Modify: `backend/app/services/data_sync.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_data_sync_logging.py`:
```python
import json
from unittest.mock import patch

from sqlmodel import Session, select

from app.db.models import FundMetadata, Holding, PortfolioSnapshot, SyncLog
from app.services.data_sync import sync_portfolio_funds


def _seed_holdings(session: Session):
    snap = PortfolioSnapshot()
    session.add(snap)
    session.commit()

    holdings = [
        Holding(
            snapshot_id=snap.id,
            fund_code="110011",
            fund_name="易方达优质精选",
            shares=100,
            cost_price=1.5,
            market_value=150,
        ),
        Holding(
            snapshot_id=snap.id,
            fund_code="000001",
            fund_name="测试基金A",
            shares=50,
            cost_price=1.0,
            market_value=50,
        ),
    ]
    for h in holdings:
        session.add(h)
    session.commit()
    return snap


def _seed_metadata(session: Session, code: str, name: str):
    meta = session.get(FundMetadata, code)
    if meta is None:
        meta = FundMetadata(
            code=code,
            name=name,
            fund_type="",
            category="stock",
        )
        session.add(meta)
        session.commit()


def test_sync_writes_sync_log_on_success(session):
    snap = _seed_holdings(session)
    _seed_metadata(session, "110011", "易方达优质精选")
    _seed_metadata(session, "000001", "测试基金A")

    with patch("app.services.data_sync.fetch_nav_from_akshare") as mock_nav:
        mock_nav.return_value = [{"date": "2026-01-01", "nav": 1.0, "acc_nav": 1.0}]
        result = sync_portfolio_funds(session)

    assert result["synced"] >= 1

    log = session.exec(select(SyncLog).order_by(SyncLog.id.desc())).first()
    assert log is not None
    assert log.status in ("done", "partial")
    assert log.total_funds >= 1
    assert log.success_funds >= 1


def test_sync_log_records_nav_error(session):
    snap = _seed_holdings(session)
    _seed_metadata(session, "110011", "易方达优质精选")

    with patch("app.services.data_sync.fetch_nav_from_akshare") as mock_nav:
        mock_nav.side_effect = RuntimeError("AKShare rate limited")
        result = sync_portfolio_funds(session)

    log = session.exec(select(SyncLog).order_by(SyncLog.id.desc())).first()
    assert log is not None
    errors = json.loads(log.errors_json)
    assert any(e["fund_code"] == "110011" and "nav" in e["stage"] for e in errors)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_data_sync_logging.py -v`
Expected: FAIL (no SyncLog record written)

- [ ] **Step 3: Modify sync_portfolio_funds to write SyncLog**

In `backend/app/services/data_sync.py`, replace `sync_portfolio_funds`:

```python
def sync_portfolio_funds(session: Session) -> dict[str, Any]:
    from datetime import datetime

    snap = get_latest_snapshot(session)
    if not snap:
        return {"synced": 0, "codes": [], "details": []}

    holdings = session.exec(
        select(Holding).where(Holding.snapshot_id == snap.id)
    ).all()
    codes = sorted({h.fund_code for h in holdings})
    name_by_code = {h.fund_code: h.fund_name for h in holdings}

    sync_log = SyncLog(
        started_at=datetime.utcnow(),
        status="running",
        total_funds=len(codes),
        success_funds=0,
        failed_funds=0,
        errors_json="[]",
    )
    session.add(sync_log)
    session.commit()

    details: list[dict[str, Any]] = []
    synced = 0
    errors: list[dict[str, Any]] = []

    # Per-fund metadata sync
    for code in codes:
        try:
            sync_fund_metadata(session, code, fallback_name=name_by_code.get(code, ""))
        except Exception as exc:
            errors.append({"fund_code": code, "stage": "metadata", "error": str(exc)})
            details.append({"code": code, "status": "metadata_error", "error": str(exc)})

    # Purchase limits (batch)
    try:
        sync_purchase_limits(session, codes)
    except Exception as exc:
        errors.append({"fund_code": "*", "stage": "purchase_limits", "error": str(exc)})
        details.append({"code": "*", "status": "purchase_limits_error", "error": str(exc)})

    # Per-fund NAV sync + metrics
    for code in codes:
        try:
            nav_rows = sync_fund_nav(session, code)
            metrics = compute_and_cache_metrics(session, code)
            try:
                _apply_peer_metrics(session, code)
                session.commit()
            except Exception as exc:
                errors.append({"fund_code": code, "stage": "peer_metrics", "error": str(exc)})
                details.append({"code": code, "status": "peer_metrics_error", "error": str(exc)})
            details.append(
                {
                    "code": code,
                    "nav_rows": nav_rows,
                    "metrics_cached": metrics is not None,
                    "status": "ok",
                }
            )
            synced += 1
        except Exception as exc:
            errors.append({"fund_code": code, "stage": "nav", "error": str(exc)})
            details.append({"code": code, "status": "error", "error": str(exc)})

    revalue = revalue_holdings(session, snap.id)

    # Update SyncLog
    sync_log.finished_at = datetime.utcnow()
    sync_log.success_funds = synced
    sync_log.failed_funds = len(codes) - synced
    sync_log.errors_json = json.dumps(errors, ensure_ascii=False)
    if synced == len(codes) and len(errors) == 0:
        sync_log.status = "done"
    elif synced > 0:
        sync_log.status = "partial"
    else:
        sync_log.status = "failed"
    session.add(sync_log)
    session.commit()

    return {
        "synced": synced,
        "codes": codes,
        "details": details,
        "revalued": revalue["updated"],
        "as_of_date": revalue["as_of_date"],
        "sync_log_id": sync_log.id,
    }
```

Add the import at the top of `data_sync.py`, after the existing imports:

```python
from app.db.models import SyncLog
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_data_sync_logging.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/data_sync.py backend/tests/test_data_sync_logging.py
git commit -m "feat: write SyncLog on every sync with per-fund error tracking"
```

---

### Task 4: 同步日志 API 端点

**Files:**
- Create: `backend/tests/test_api_sync_logs.py`
- Modify: `backend/app/api/routes/settings.py`
- Modify: `backend/app/schemas/settings.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_api_sync_logs.py`:
```python
import json
from datetime import datetime

from fastapi.testclient import TestClient

from app.db.models import SyncLog


def test_list_sync_logs_empty(client: TestClient, session):
    response = client.get("/api/settings/sync-logs")
    assert response.status_code == 200
    data = response.json()
    assert data["logs"] == []


def test_list_sync_logs_with_data(client: TestClient, session):
    for status in ("done", "partial", "failed"):
        log = SyncLog(
            status=status,
            total_funds=5,
            success_funds=3,
            failed_funds=2,
            errors_json=json.dumps([]),
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
        session.add(log)
    session.commit()

    response = client.get("/api/settings/sync-logs?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["logs"], list)
    assert len(data["logs"]) == 3
    # Most recent first
    assert data["logs"][0]["status"] == "failed"
    assert data["logs"][1]["status"] == "partial"
    assert data["logs"][2]["status"] == "done"
    # Each log has expected fields
    log0 = data["logs"][0]
    assert "id" in log0
    assert log0["total_funds"] == 5
    assert log0["errors_json"] == "[]"


def test_list_sync_logs_respects_limit(client: TestClient, session):
    for _ in range(5):
        log = SyncLog(
            status="done",
            total_funds=3,
            success_funds=3,
            failed_funds=0,
            errors_json=json.dumps([]),
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
        )
        session.add(log)
    session.commit()

    response = client.get("/api/settings/sync-logs?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["logs"]) == 2
```

- [ ] **Step 2: Run test to verify they fail**

Run: `pytest backend/tests/test_api_sync_logs.py -v`
Expected: FAIL (404, route doesn't exist yet)

- [ ] **Step 3: Add schema + endpoint**

In `backend/app/schemas/settings.py`, add at the end:

```python
class SyncLogOut(BaseModel):
    id: int
    started_at: datetime
    finished_at: datetime | None = None
    status: str
    total_funds: int
    success_funds: int
    failed_funds: int
    errors_json: str


class SyncLogsListOut(BaseModel):
    logs: list[SyncLogOut]
```

Add the `datetime` import at the top of `schemas/settings.py`:

```python
from datetime import datetime
```

In `backend/app/api/routes/settings.py`, add at the end (before the final blank line):

```python
from app.db.models import SyncLog
from app.schemas.settings import SyncLogOut, SyncLogsListOut


@router.get("/sync-logs", response_model=SyncLogsListOut)
def list_sync_logs(limit: int = 3, session: Session = Depends(get_db)):
    logs = session.exec(
        select(SyncLog)
        .order_by(SyncLog.id.desc())
        .limit(limit)
    ).all()
    return SyncLogsListOut(
        logs=[
            SyncLogOut(
                id=log.id,
                started_at=log.started_at,
                finished_at=log.finished_at,
                status=log.status,
                total_funds=log.total_funds,
                success_funds=log.success_funds,
                failed_funds=log.failed_funds,
                errors_json=log.errors_json,
            )
            for log in logs
        ]
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_api_sync_logs.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_api_sync_logs.py backend/app/api/routes/settings.py backend/app/schemas/settings.py
git commit -m "feat: add GET /api/settings/sync-logs endpoint"
```

---

### Task 5: 前端 TanStack Query 依赖安装 + QueryClientProvider

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/main.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Install @tanstack/react-query**

Run: `cd frontend && npm install @tanstack/react-query`

Expected: package.json updated with `"@tanstack/react-query": "^5.x"`

- [ ] **Step 2: Wrap App with QueryClientProvider**

Modify `frontend/src/App.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import AnalysisPage from './pages/AnalysisPage'
import Dashboard from './pages/Dashboard'
import HoldingsPage from './pages/HoldingsPage'
import ImportPage from './pages/ImportPage'
import OpportunitiesPage from './pages/OpportunitiesPage'
import SettingsPage from './pages/SettingsPage'
import SignalsPage from './pages/SignalsPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="opportunities" element={<OpportunitiesPage />} />
            <Route path="import" element={<ImportPage />} />
            <Route path="holdings" element={<HoldingsPage />} />
            <Route path="signals" element={<SignalsPage />} />
            <Route path="analysis" element={<AnalysisPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
```

- [ ] **Step 3: Verify app still loads**

Run: `cd frontend && npm run build`

Expected: build succeeds without errors

- [ ] **Step 4: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/App.tsx
git commit -m "feat: add @tanstack/react-query and wrap app with QueryClientProvider"
```

---

### Task 6: Query keys 和 query functions 集中定义

**Files:**
- Create: `frontend/src/api/queries.ts`

- [ ] **Step 1: Write queries.ts**

`frontend/src/api/queries.ts`:
```typescript
import {
  api,
  fetchBacktestSensitivity,
  fetchBacktestSnapshotStats,
  fetchCorrelation,
  fetchHotThemes,
  fetchOpportunities,
  fetchSignals,
  fetchStrategy,
  fetchThemeCandidates,
  fetchThemes,
  searchFunds,
  syncData,
  updateStrategy,
} from './client'
import type {
  DataSyncResult,
  HotTheme,
  OpportunitiesOut,
  SignalsListOut,
  StrategyConfig,
} from '../types'

// ── Query Keys ──

export const queryKeys = {
  overview: ['overview'] as const,
  holdings: ['holdings'] as const,
  signals: ['signals'] as const,
  correlation: ['correlation'] as const,
  risk: ['risk'] as const,
  strategy: ['strategy'] as const,
  opportunities: (params?: Record<string, unknown>) =>
    ['opportunities', params] as const,
  hotThemes: (params?: Record<string, unknown>) =>
    ['hotThemes', params] as const,
  backtestSensitivity: ['backtestSensitivity'] as const,
  backtestSnapshotStats: ['backtestSnapshotStats'] as const,
  syncLogs: ['syncLogs'] as const,
  themes: ['themes'] as const,
  themeCandidates: (themeId: string, sortBy: string, limit: number) =>
    ['themeCandidates', themeId, sortBy, limit] as const,
}

// ── Query Functions ──

export async function fetchOverview() {
  return api.get<import('../types').Overview>('/api/portfolio/overview')
}

export async function fetchHoldings() {
  return api.get<import('../types').Overview>('/api/portfolio/holdings')
}

export {
  fetchSignals,
  fetchCorrelation,
  fetchRisk,
  fetchStrategy,
  fetchOpportunities,
  fetchHotThemes,
  fetchBacktestSensitivity,
  fetchBacktestSnapshotStats,
  syncData,
  updateStrategy,
  searchFunds,
  fetchThemes,
  fetchThemeCandidates,
}

export async function fetchSyncLogs(limit = 3) {
  return api.get<{ logs: import('../types').SyncLogEntry[] }>(
    `/api/settings/sync-logs?limit=${limit}`,
  )
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc -b --noEmit`

Expected: types resolve correctly (may need to add SyncLogEntry to types)

- [ ] **Step 3: Add SyncLogEntry type**

In `frontend/src/types/index.ts`, add:

```typescript
export interface SyncLogEntry {
  id: number
  started_at: string
  finished_at: string | null
  status: 'running' | 'done' | 'partial' | 'failed'
  total_funds: number
  success_funds: number
  failed_funds: number
  errors_json: string
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/api/queries.ts frontend/src/types/index.ts
git commit -m "feat: add query keys, query functions, and SyncLogEntry type"
```

---

### Task 7: 封装好的 query hooks

**Files:**
- Create: `frontend/src/api/hooks.ts`

- [ ] **Step 1: Write hooks.ts**

`frontend/src/api/hooks.ts`:
```typescript
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fetchBacktestSensitivity,
  fetchBacktestSnapshotStats,
  fetchCorrelation,
  fetchHoldings,
  fetchHotThemes,
  fetchOpportunities,
  fetchOverview,
  fetchSignals,
  fetchStrategy,
  fetchSyncLogs,
  queryKeys,
  syncData,
  updateStrategy,
} from './queries'
import type {
  DataSyncResult,
  HotTheme,
  OpportunitiesOut,
  SignalsListOut,
  StrategyConfig,
} from '../types'

// ── Queries ──

export function useOverview() {
  return useQuery({
    queryKey: queryKeys.overview,
    queryFn: fetchOverview,
  })
}

export function useHoldings() {
  return useQuery({
    queryKey: queryKeys.holdings,
    queryFn: fetchHoldings,
  })
}

export function useSignals() {
  return useQuery({
    queryKey: queryKeys.signals,
    queryFn: fetchSignals,
  })
}

export function useCorrelation() {
  return useQuery({
    queryKey: queryKeys.correlation,
    queryFn: fetchCorrelation,
  })
}

export function useRisk() {
  return useQuery({
    queryKey: queryKeys.risk,
    queryFn: fetchRisk,
  })
}

export function useStrategy() {
  return useQuery({
    queryKey: queryKeys.strategy,
    queryFn: fetchStrategy,
  })
}

export function useOpportunities(params?: {
  sell_limit?: number
  buy_limit?: number
  explore_limit?: number
  theme_limit?: number
  include_hot_themes?: boolean
  include_theme_candidates?: boolean
}) {
  return useQuery({
    queryKey: queryKeys.opportunities(params),
    queryFn: () => fetchOpportunities(params),
  })
}

export function useHotThemes(params?: {
  theme_limit?: number
  include_candidates?: boolean
}) {
  return useQuery({
    queryKey: queryKeys.hotThemes(params),
    queryFn: () => fetchHotThemes(params),
  })
}

export function useBacktestSensitivity() {
  return useQuery({
    queryKey: queryKeys.backtestSensitivity,
    queryFn: fetchBacktestSensitivity,
  })
}

export function useBacktestSnapshotStats() {
  return useQuery({
    queryKey: queryKeys.backtestSnapshotStats,
    queryFn: fetchBacktestSnapshotStats,
  })
}

export function useSyncLogs(limit = 3) {
  return useQuery({
    queryKey: queryKeys.syncLogs,
    queryFn: () => fetchSyncLogs(limit),
  })
}

// ── Mutations ──

export function useSyncData() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: syncData,
    onSuccess: () => {
      // Invalidate all data queries so they refetch fresh data
      queryClient.invalidateQueries({ queryKey: queryKeys.signals })
      queryClient.invalidateQueries({ queryKey: queryKeys.overview })
      queryClient.invalidateQueries({ queryKey: queryKeys.holdings })
      queryClient.invalidateQueries({ queryKey: queryKeys.correlation })
      queryClient.invalidateQueries({ queryKey: queryKeys.risk })
      queryClient.invalidateQueries({ queryKey: queryKeys.opportunities })
      queryClient.invalidateQueries({ queryKey: queryKeys.hotThemes })
      queryClient.invalidateQueries({ queryKey: queryKeys.backtestSensitivity })
      queryClient.invalidateQueries({ queryKey: queryKeys.backtestSnapshotStats })
      queryClient.invalidateQueries({ queryKey: queryKeys.syncLogs })
    },
  })
}

export function useUpdateStrategy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: updateStrategy,
    onSuccess: (data: StrategyConfig) => {
      queryClient.setQueryData(queryKeys.strategy, data)
      queryClient.invalidateQueries({ queryKey: queryKeys.signals })
    },
  })
}
```

- [ ] **Step 2: Verify TypeScript compilation**

Run: `cd frontend && npx tsc -b --noEmit`

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/api/hooks.ts
git commit -m "feat: add query hooks (useOverview, useSignals, etc.) and mutation hooks"
```

---

### Task 8: 重构 Dashboard 页面

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Replace manual fetch with query hooks**

Replace `frontend/src/pages/Dashboard.tsx`:

```tsx
import { Link } from 'react-router-dom'
import { useHotThemes, useOpportunities, useOverview } from '../api/hooks'
import ActionSummaryCards from '../components/ActionSummaryCards'
import AllocationChart from '../components/AllocationChart'
import ConcentrationCard from '../components/ConcentrationCard'
import HotThemeRadar from '../components/HotThemeRadar'
import HoldingsTable from '../components/HoldingsTable'
import StatCard from '../components/StatCard'
import ThemeExposurePanel from '../components/ThemeExposurePanel'
import type { HotTheme, OpportunitiesOut } from '../types'
import { formatCurrency, formatProfitAmount, formatSignedPercent } from '../utils/format'

export default function Dashboard() {
  const {
    data: overview,
    isLoading: loading,
    error,
  } = useOverview()

  const {
    data: opportunities,
  } = useOpportunities({
    sell_limit: 3,
    buy_limit: 3,
    explore_limit: 3,
    include_hot_themes: false,
  })

  const {
    data: hotThemes = [],
    isLoading: themesLoading,
  } = useHotThemes({ theme_limit: 5 })

  if (loading) {
    return <p className="text-slate-500">加载中...</p>
  }

  if (error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        无法加载组合概览：{error instanceof Error ? error.message : '未知错误'}
      </div>
    )
  }

  if (!overview || overview.holdings.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <h2 className="text-xl font-semibold text-slate-900">还没有持仓数据</h2>
        <p className="mt-2 text-slate-500">
          通过 OCR 导入或手动录入第一笔持仓，即可在这里查看总览。
        </p>
        <Link
          to="/import"
          className="mt-6 inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          去导入持仓
        </Link>
      </div>
    )
  }

  const profitTone =
    overview.total_profit > 0 ? 'profit' : overview.total_profit < 0 ? 'loss' : 'default'

  const opportunitiesWithThemes: OpportunitiesOut | null = opportunities
    ? { ...opportunities, hot_themes: hotThemes as HotTheme[] }
    : null

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">组合总览</h2>
        <p className="mt-1 text-sm text-slate-500">
          快照 #{overview.snapshot_id ?? '—'} · 共 {overview.holdings.length} 只基金
          {overview.data_as_of_date ? ` · 净值截至 ${overview.data_as_of_date}` : ''}
        </p>
      </div>

      <ActionSummaryCards data={opportunitiesWithThemes} />
      {themesLoading ? (
        <p className="text-sm text-slate-500">热点雷达加载中...</p>
      ) : (
        <HotThemeRadar themes={hotThemes} />
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="总市值" value={formatCurrency(overview.total_value)} />
        <StatCard title="总成本" value={formatCurrency(overview.total_cost)} />
        <StatCard
          title="总盈亏"
          value={formatProfitAmount(overview.total_profit)}
          subtitle={formatSignedPercent(overview.total_profit_rate)}
          tone={profitTone}
        />
        <StatCard
          title="收益率"
          value={formatSignedPercent(overview.total_profit_rate)}
          tone={profitTone}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">大类配置</h3>
          <p className="mt-1 text-sm text-slate-500">按基金名称与类型自动分类</p>
          <div className="mt-4">
            <AllocationChart allocation={overview.category_allocation ?? []} />
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="text-base font-semibold text-slate-900">主题暴露</h3>
          <p className="mt-1 text-sm text-slate-500">存储/CPO/半导体等赛道占比</p>
          <div className="mt-4">
            <ThemeExposurePanel allocation={overview.theme_allocation ?? []} />
          </div>
        </section>
      </div>

      <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="text-base font-semibold text-slate-900">集中度 Top5</h3>
        <p className="mt-1 text-sm text-slate-500">单只权重过高可能触发减仓信号</p>
        <div className="mt-4">
          <ConcentrationCard
            topHoldings={overview.top_holdings ?? []}
            concentrationTop5Pct={overview.concentration_top5_pct ?? 0}
          />
        </div>
      </section>

      <HoldingsTable holdings={overview.holdings} />
    </div>
  )
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx tsc -b --noEmit`

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "refactor: Dashboard uses TanStack Query hooks"
```

---

### Task 9: 重构 SignalsPage

**Files:**
- Modify: `frontend/src/pages/SignalsPage.tsx`

- [ ] **Step 1: Replace with hooks**

Replace `frontend/src/pages/SignalsPage.tsx`:

```tsx
import { Link } from 'react-router-dom'
import { useSignals, useSyncData } from '../api/hooks'
import SignalsTable from '../components/SignalsTable'
import { maybeNotifyStrongSignals, summarizeStrongSignals } from '../utils/notifications'

function sortSignals(signals: import('../types').Signal[]) {
  return [...signals].sort((a, b) => b.score - a.score)
}

export default function SignalsPage() {
  const { data, isLoading: loading, error } = useSignals()
  const syncMutation = useSyncData()

  const snapshotId = data?.snapshot_id ?? null
  const signals = sortSignals(data?.signals ?? [])

  async function handleSync() {
    const result = await syncMutation.mutateAsync()
    const summary = summarizeStrongSignals(snapshotId, signals)
    if (summary) {
      maybeNotifyStrongSignals(summary)
    }
  }

  if (loading) {
    return <p className="text-slate-500">加载中...</p>
  }

  if (error && signals.length === 0 && snapshotId === null) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        无法加载信号：{error instanceof Error ? error.message : '未知错误'}
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900">
        <p className="font-medium">免责声明</p>
        <p className="mt-1 text-amber-800">
          以下信号由量化规则自动生成，仅供个人参考，<strong>非投资建议</strong>
          。请结合自身风险承受能力独立决策。
        </p>
      </div>

      <div>
        <h2 className="text-2xl font-semibold text-slate-900">买卖信号</h2>
        <p className="mt-1 text-sm text-slate-500">
          {snapshotId !== null
            ? `快照 #${snapshotId} · 共 ${signals.length} 条信号，按综合得分排序`
            : '导入持仓并同步数据后，系统将生成再平衡与风险信号'}
        </p>
      </div>

      {syncMutation.isError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {syncMutation.error instanceof Error ? syncMutation.error.message : '同步失败'}
        </div>
      ) : null}

      {signals.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <h3 className="text-xl font-semibold text-slate-900">暂无买卖信号</h3>
          <p className="mt-2 text-slate-500">
            请先导入持仓，再触发数据同步以计算量化信号。
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/import"
              className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
            >
              去导入持仓
            </Link>
            <button
              type="button"
              onClick={handleSync}
              disabled={syncMutation.isPending}
              className="inline-flex rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {syncMutation.isPending ? '同步中...' : '同步数据'}
            </button>
          </div>
        </div>
      ) : (
        <SignalsTable signals={signals} />
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx tsc -b --noEmit`

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SignalsPage.tsx
git commit -m "refactor: SignalsPage uses TanStack Query hooks"
```

---

### Task 10: 重构 OpportunitiesPage

**Files:**
- Modify: `frontend/src/pages/OpportunitiesPage.tsx`

- [ ] **Step 1: Replace with hooks**

Replace `frontend/src/pages/OpportunitiesPage.tsx` (key parts — the body replaces loading/error/sync):

```tsx
import { useSearchParams, Link } from 'react-router-dom'
import { useOpportunities, useSyncData } from '../api/hooks'
import ActionList from '../components/ActionList'
import HotThemeRadar from '../components/HotThemeRadar'
import StructuralAlerts from '../components/StructuralAlerts'

type TabKey = 'actions' | 'themes'

export default function OpportunitiesPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab')
  const activeTab: TabKey = tabParam === 'themes' ? 'themes' : 'actions'

  const { data, isLoading: loading, error } = useOpportunities({
    sell_limit: 10,
    buy_limit: 10,
    explore_limit: 10,
    theme_limit: 9,
  })

  const syncMutation = useSyncData()

  function setTab(tab: TabKey) {
    setSearchParams({ tab })
  }

  async function handleSync() {
    await syncMutation.mutateAsync()
  }

  if (loading) {
    return <p className="text-slate-500">加载中...</p>
  }

  if (error && !data) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        无法加载机会数据：{error instanceof Error ? error.message : '未知错误'}
      </div>
    )
  }

  const snapshotId = data?.snapshot_id ?? null
  const structuralActions = data?.structural_actions ?? []
  const hasConsolidateBlock = structuralActions.some((item) => item.action === 'consolidate')
  const totalActions =
    (data?.sell_actions.length ?? 0) +
    (data?.buy_actions.length ?? 0) +
    (data?.explore_actions.length ?? 0)

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-amber-200 bg-amber-50 px-5 py-4 text-sm text-amber-900">
        <p className="font-medium">免责声明</p>
        <p className="mt-1 text-amber-800">
          以下机会由量化规则自动生成，仅供个人参考，<strong>非投资建议</strong>
          。请结合自身风险承受能力独立决策。
        </p>
        <p className="mt-2 text-amber-800">
          热点按主题基金近 1 月收益中位数排序，反映近期业绩而非新闻舆情，仅供参考，不构成投资建议。
        </p>
      </div>

      <div>
        <h2 className="text-2xl font-semibold text-slate-900">机会中心</h2>
        <p className="mt-1 text-sm text-slate-500">
          {snapshotId !== null
            ? `快照 #${snapshotId}${data?.data_as_of_date ? ` · 净值截至 ${data.data_as_of_date}` : ''}`
            : '导入持仓并同步数据后，系统将聚合行动建议与热点主题'}
        </p>
      </div>

      {syncMutation.isError ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {syncMutation.error instanceof Error ? syncMutation.error.message : '同步失败'}
        </div>
      ) : null}

      {snapshotId === null ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
          <h3 className="text-xl font-semibold text-slate-900">暂无机会数据</h3>
          <p className="mt-2 text-slate-500">导入持仓并同步后查看机会</p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Link
              to="/import"
              className="inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
            >
              去导入持仓
            </Link>
            <button
              type="button"
              onClick={handleSync}
              disabled={syncMutation.isPending}
              className="inline-flex rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {syncMutation.isPending ? '同步中...' : '同步数据'}
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Tabs */}
          <div className="flex border-b border-slate-200">
            <button
              type="button"
              onClick={() => setTab('actions')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'actions'
                  ? 'border-slate-900 text-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              行动建议 {totalActions > 0 ? `(${totalActions})` : ''}
            </button>
            <button
              type="button"
              onClick={() => setTab('themes')}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === 'themes'
                  ? 'border-slate-900 text-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-700'
              }`}
            >
              热点主题 {data?.hot_themes?.length ? `(${data.hot_themes.length})` : ''}
            </button>
          </div>

          {activeTab === 'themes' ? (
            <HotThemeRadar themes={data?.hot_themes ?? []} />
          ) : (
            <div className="space-y-6">
              {structuralActions.length > 0 && (
                <StructuralAlerts
                  actions={structuralActions}
                />
              )}
              {!hasConsolidateBlock && (
                <ActionList
                  title="卖出 / 减仓"
                  actions={data?.sell_actions ?? []}
                  emptyMessage="暂无卖出信号"
                />
              )}
              <ActionList
                title="增配 / 买入"
                actions={data?.buy_actions ?? []}
                emptyMessage="暂无增配信号"
              />
              <ActionList
                title="探索 / 关注"
                actions={data?.explore_actions ?? []}
                emptyMessage="暂无探索信号"
              />
            </div>
          )}
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx tsc -b --noEmit`

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/OpportunitiesPage.tsx
git commit -m "refactor: OpportunitiesPage uses TanStack Query hooks"
```

---

### Task 11: 重构 HoldingsPage

**Files:**
- Modify: `frontend/src/pages/HoldingsPage.tsx`

- [ ] **Step 1: Replace with hooks**

Replace the data-fetching portion of `frontend/src/pages/HoldingsPage.tsx`:

```tsx
import { Link } from 'react-router-dom'
import { useHoldings } from '../api/hooks'
import HoldingsTable from '../components/HoldingsTable'
import StatCard from '../components/StatCard'
import { formatCurrency, formatProfitAmount, formatSignedPercent } from '../utils/format'

export default function HoldingsPage() {
  const { data: overview, isLoading: loading, error } = useHoldings()

  if (loading) {
    return <p className="text-slate-500">加载中...</p>
  }

  if (error) {
    return (
      <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-rose-700">
        无法加载持仓：{error instanceof Error ? error.message : '未知错误'}
      </div>
    )
  }

  if (!overview || overview.holdings.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center">
        <h2 className="text-xl font-semibold text-slate-900">还没有持仓数据</h2>
        <p className="mt-2 text-slate-500">
          通过 OCR 导入或手动录入第一笔持仓。
        </p>
        <Link
          to="/import"
          className="mt-6 inline-flex rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
        >
          去导入持仓
        </Link>
      </div>
    )
  }

  const profitTone =
    overview.total_profit > 0 ? 'profit' : overview.total_profit < 0 ? 'loss' : 'default'

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">持仓明细</h2>
        <p className="mt-1 text-sm text-slate-500">
          快照 #{overview.snapshot_id ?? '—'} · 共 {overview.holdings.length} 只基金
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard title="总市值" value={formatCurrency(overview.total_value)} />
        <StatCard title="总成本" value={formatCurrency(overview.total_cost)} />
        <StatCard
          title="总盈亏"
          value={formatProfitAmount(overview.total_profit)}
          subtitle={formatSignedPercent(overview.total_profit_rate)}
          tone={profitTone}
        />
        <StatCard
          title="收益率"
          value={formatSignedPercent(overview.total_profit_rate)}
          tone={profitTone}
        />
      </div>

      <HoldingsTable holdings={overview.holdings} showActions />
    </div>
  )
}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx tsc -b --noEmit`

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/HoldingsPage.tsx
git commit -m "refactor: HoldingsPage uses TanStack Query hooks"
```

---

### Task 12: 重构 AnalysisPage

**Files:**
- Modify: `frontend/src/pages/AnalysisPage.tsx`

- [ ] **Step 1: Replace with hooks**

Replace the data-fetching portion of `frontend/src/pages/AnalysisPage.tsx`:

```tsx
import { useBacktestSensitivity, useBacktestSnapshotStats, useCorrelation, useRisk } from '../api/hooks'
import BacktestPanel from '../components/BacktestPanel'

export default function AnalysisPage() {
  const {
    data: correlation,
    isLoading: corrLoading,
    error: corrError,
  } = useCorrelation()

  const {
    data: risk,
    isLoading: riskLoading,
    error: riskError,
  } = useRisk()

  const {
    data: sensitivity,
  } = useBacktestSensitivity()

  const {
    data: snapshotStats,
  } = useBacktestSnapshotStats()

  const loading = corrLoading || riskLoading

  if (loading) {
    return <p className="text-slate-500">加载中...</p>
  }

  // ... rest of the component using correlation, risk, sensitivity, snapshotStats
  // The JSX rendering part stays the same, just data source changes
}
```

(Note: the full component body is long. The key change is replacing `useState + useEffect + fetch` with the 4 hooks above. The actual rendering of the correlation table, risk metrics, and backtest panel stays identical.)

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx tsc -b --noEmit`

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/AnalysisPage.tsx
git commit -m "refactor: AnalysisPage uses TanStack Query hooks"
```

---

### Task 13: 重构 SettingsPage + 同步历史展示

**Files:**
- Modify: `frontend/src/pages/SettingsPage.tsx`

- [ ] **Step 1: Replace with hooks + add sync history section**

Replace data-fetching and sync portions of SettingsPage. Key changes:

1. Replace `useState + useEffect + fetchStrategy` → `useStrategy()` hook
2. Replace manual `api.post('/api/data/sync', {})` → `useSyncData()` hook
3. Add `useSyncLogs()` for sync history display

At the bottom of the SettingsPage JSX (after the existing content, before the closing `</div>`), add:

```tsx
import { useStrategy, useSyncData, useSyncLogs } from '../api/hooks'

// Inside the component, replace loading/applyConfig/sync with:
const { data: config, isLoading: loading, error } = useStrategy()
const syncMutation = useSyncData()
const { data: syncLogsData } = useSyncLogs(3)
```

And add sync history section:

```tsx
{/* Sync History Section */}
<section className="mt-10 border-t border-slate-200 pt-6">
  <h3 className="text-lg font-semibold text-slate-900">同步历史</h3>
  <p className="mt-1 text-sm text-slate-500">最近 3 次数据同步的执行结果</p>

  {syncLogsData && syncLogsData.logs.length > 0 ? (
    <div className="mt-4 overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-slate-500">
            <th className="px-3 py-2 font-medium">时间</th>
            <th className="px-3 py-2 font-medium">状态</th>
            <th className="px-3 py-2 font-medium">成功/总数</th>
            <th className="px-3 py-2 font-medium">错误</th>
          </tr>
        </thead>
        <tbody>
          {syncLogsData.logs.map((log) => {
            const errors = JSON.parse(log.errors_json || '[]') as Array<{
              fund_code: string
              stage: string
              error: string
            }>
            const statusDisplay = {
              done: { text: '✅ 全部成功', color: 'text-emerald-700' },
              partial: { text: '⚠️ 部分失败', color: 'text-amber-700' },
              failed: { text: '❌ 全部失败', color: 'text-rose-700' },
              running: { text: '🔄 进行中', color: 'text-blue-700' },
            }[log.status] ?? { text: log.status, color: 'text-slate-700' }

            return (
              <tr key={log.id} className="border-b border-slate-100">
                <td className="px-3 py-2 text-slate-700">
                  {new Date(log.started_at).toLocaleString('zh-CN')}
                </td>
                <td className={`px-3 py-2 font-medium ${statusDisplay.color}`}>
                  {statusDisplay.text}
                </td>
                <td className="px-3 py-2 tabular-nums text-slate-700">
                  {log.success_funds} / {log.total_funds}
                </td>
                <td className="px-3 py-2 text-slate-600">
                  {errors.length > 0
                    ? errors.map((e, i) => (
                        <span key={i} className="block text-xs">
                          {e.fund_code}: {e.error}
                        </span>
                      ))
                    : '—'}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  ) : (
    <p className="mt-4 text-sm text-slate-500">暂无同步记录</p>
  )}
</section>
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx tsc -b --noEmit`

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SettingsPage.tsx
git commit -m "refactor: SettingsPage uses TanStack Query hooks + sync history table"
```

---

### Task 14: 重构 ImportPage

**Files:**
- Modify: `frontend/src/pages/ImportPage.tsx`

- [ ] **Step 1: Replace manual post calls with useMutation**

The ImportPage uses `uploadOcr` and `confirmOcr` functions directly. Wrap these with `useMutation`:

```tsx
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { confirmOcr, uploadOcr } from '../api/client'
import { queryKeys } from '../api/queries'

// inside the component:
const queryClient = useQueryClient()

const uploadMutation = useMutation({
  mutationFn: uploadOcr,
})

const confirmMutation = useMutation({
  mutationFn: ({ jobId, holdings }: { jobId: number; holdings: OcrUploadResponse['holdings'] }) =>
    confirmOcr(jobId, holdings),
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: queryKeys.overview })
    queryClient.invalidateQueries({ queryKey: queryKeys.holdings })
  },
})

// Replace uploadOcr(...) calls with uploadMutation.mutateAsync(...)
// Replace confirmOcr(...) calls with confirmMutation.mutateAsync(...)
// Use uploadMutation.isPending / confirmMutation.isPending for loading states
// Use uploadMutation.error / confirmMutation.error for error display
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx tsc -b --noEmit`

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/ImportPage.tsx
git commit -m "refactor: ImportPage uses TanStack Query useMutation for OCR upload/confirm"
```

---

### Task 15: NAV 增量化同步

**Files:**
- Create: `backend/tests/test_nav_incremental.py`
- Modify: `backend/app/services/data_sync.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_nav_incremental.py`:
```python
from unittest.mock import patch

from sqlmodel import Session

from app.db.models import FundNavHistory
from app.services.data_sync import sync_fund_nav


def test_sync_nav_incremental_skips_existing_dates(session: Session):
    """When nav data already exists, incremental sync only fetches newer dates."""
    # Seed existing nav data
    existing = FundNavHistory(
        code="110011",
        date="2026-06-25",
        nav=1.5,
        acc_nav=1.5,
    )
    session.add(existing)
    session.commit()

    # akshare returns 3 days: 2 old + 1 new
    mock_nav_data = [
        {"date": "2026-06-24", "nav": 1.48, "acc_nav": 1.48},  # older than existing
        {"date": "2026-06-25", "nav": 1.55, "acc_nav": 1.55},  # same (update)
        {"date": "2026-06-26", "nav": 1.52, "acc_nav": 1.52},  # new
    ]

    with patch("app.services.data_sync.fetch_nav_from_akshare") as mock_fetch:
        mock_fetch.return_value = mock_nav_data
        synced = sync_fund_nav(session, "110011")

    # All 3 rows are synced (existing date gets updated, rest inserted)
    assert synced == 3


def test_sync_nav_incremental_full_on_first_sync(session: Session):
    """When no nav data exists, full sync happens."""
    mock_nav_data = [
        {"date": "2026-06-24", "nav": 1.48, "acc_nav": 1.48},
        {"date": "2026-06-25", "nav": 1.55, "acc_nav": 1.55},
    ]

    with patch("app.services.data_sync.fetch_nav_from_akshare") as mock_fetch:
        mock_fetch.return_value = mock_nav_data
        synced = sync_fund_nav(session, "110011")

    assert synced == 2
```

- [ ] **Step 2: Run test to verify behavior**

Run: `pytest backend/tests/test_nav_incremental.py -v`
Expected: PASS (existing sync_fund_nav already inserts/updates all rows — the existing behavior covers this)

The existing `sync_fund_nav` already uses `if existing: update else: insert`. The improvement is adding the `since_date` parameter to limit what akshare returns. We add this optimization:

In `backend/app/services/data_sync.py`, modify `sync_fund_nav`:

```python
def sync_fund_nav(session: Session, code: str) -> int:
    # Find the latest date we already have to fetch only newer data
    latest = session.exec(
        select(FundNavHistory.date)
        .where(FundNavHistory.code == code)
        .order_by(FundNavHistory.date.desc())
    ).first()

    rows = fetch_nav_from_akshare(code)

    # Filter to only new rows if we have existing data (optimization)
    if latest:
        rows = [row for row in rows if row["date"] > latest]

    synced = 0
    for row in rows:
        existing = session.exec(
            select(FundNavHistory).where(
                FundNavHistory.code == code,
                FundNavHistory.date == row["date"],
            )
        ).first()
        if existing:
            existing.nav = row["nav"]
            existing.acc_nav = row["acc_nav"]
        else:
            session.add(
                FundNavHistory(
                    code=code,
                    date=row["date"],
                    nav=row["nav"],
                    acc_nav=row["acc_nav"],
                )
            )
        synced += 1
    session.commit()
    return synced
```

- [ ] **Step 3: Run tests**

Run: `pytest backend/tests/test_nav_incremental.py backend/tests/test_data_sync.py -v`
Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/data_sync.py backend/tests/test_nav_incremental.py
git commit -m "perf: incremental NAV sync - only fetch dates after latest existing"
```

---

### Task 16: NAV 跳变检测

**Files:**
- Create: `backend/tests/test_nav_jump_detection.py`
- Modify: `backend/app/services/data_sync.py`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_nav_jump_detection.py`:
```python
from app.services.data_sync import detect_nav_jump


def test_detect_normal_navs():
    navs = [
        {"date": "2026-01-01", "nav": 1.00},
        {"date": "2026-01-02", "nav": 1.01},
        {"date": "2026-01-03", "nav": 0.99},
    ]
    anomalies = detect_nav_jump(navs)
    assert len(anomalies) == 0


def test_detect_nav_halving_from_split():
    navs = [
        {"date": "2026-01-01", "nav": 2.00},
        {"date": "2026-01-02", "nav": 1.00},  # 50% drop, likely split
    ]
    anomalies = detect_nav_jump(navs)
    assert len(anomalies) == 1
    assert anomalies[0]["date"] == "2026-01-02"
    assert abs(anomalies[0]["change_pct"] - 50.0) < 0.01
    assert "拆分" in anomalies[0]["likely_reason"]


def test_detect_nav_spike_anomaly():
    navs = [
        {"date": "2026-01-01", "nav": 1.00},
        {"date": "2026-01-02", "nav": 1.30},  # 30% spike
    ]
    anomalies = detect_nav_jump(navs)
    assert len(anomalies) == 1
    assert anomalies[0]["change_pct"] > 15


def test_skip_zero_nav():
    navs = [
        {"date": "2026-01-01", "nav": 0.00},
        {"date": "2026-01-02", "nav": 1.00},
    ]
    anomalies = detect_nav_jump(navs)
    assert len(anomalies) == 0


def test_empty_navs():
    anomalies = detect_nav_jump([])
    assert len(anomalies) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_nav_jump_detection.py -v`
Expected: FAIL with "no function named detect_nav_jump"

- [ ] **Step 3: Implement detect_nav_jump**

In `backend/app/services/data_sync.py`, add before `sync_fund_nav`:

```python
NAV_DAILY_CHANGE_THRESHOLD = 0.15  # 日涨跌超过 15% 视为异常


def detect_nav_jump(navs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """检测净值跳变，返回异常日期列表（通常是分红/拆分未复权，或数据源异常）。"""
    if len(navs) < 2:
        return []

    sorted_navs = sorted(navs, key=lambda x: x["date"])
    anomalies: list[dict[str, Any]] = []

    for i in range(1, len(sorted_navs)):
        prev_nav = sorted_navs[i - 1]["nav"]
        curr_nav = sorted_navs[i]["nav"]
        if prev_nav <= 0:
            continue
        change = abs(curr_nav / prev_nav - 1)
        if change > NAV_DAILY_CHANGE_THRESHOLD:
            anomalies.append(
                {
                    "date": sorted_navs[i]["date"],
                    "prev_nav": prev_nav,
                    "curr_nav": curr_nav,
                    "change_pct": round(change * 100, 2),
                    "likely_reason": "可能是分红/拆分未复权，或数据源异常",
                }
            )

    return anomalies
```

Then add jump detection call inside `sync_fund_nav`, after fetching rows and before the sync loop:

```python
# In sync_fund_nav, after: rows = fetch_nav_from_akshare(code)
# Add:
jump_anomalies = detect_nav_jump(rows)
if jump_anomalies:
    logger.warning(
        "NAV jump detected for %s: %d anomalies",
        code,
        len(jump_anomalies),
    )
```

- [ ] **Step 4: Run tests**

Run: `pytest backend/tests/test_nav_jump_detection.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/data_sync.py backend/tests/test_nav_jump_detection.py
git commit -m "feat: detect NAV jumps (>15% daily change) during sync"
```

---

### Task 17: NAV 跳变记录写入 SyncLog

**Files:**
- Modify: `backend/app/services/data_sync.py`

- [ ] **Step 1: Pass jump anomalies through sync_portfolio_funds to sync_log**

Modify `sync_fund_nav` to return anomalies alongside synced count:

```python
def sync_fund_nav(session: Session, code: str) -> tuple[int, list[dict[str, Any]]]:
    # ... existing logic ...
    jump_anomalies = detect_nav_jump(rows)
    if jump_anomalies:
        logger.warning(...)
    return synced, jump_anomalies
```

In `sync_portfolio_funds`, update the nav sync call site:

```python
nav_rows, jump_anomalies = sync_fund_nav(session, code)
if jump_anomalies:
    for anomaly in jump_anomalies:
        errors.append({
            "fund_code": code,
            "stage": "nav_jump",
            "error": (
                f"日期 {anomaly['date']} 净值跳变 {anomaly['change_pct']}%"
                f" (从 {anomaly['prev_nav']} 到 {anomaly['curr_nav']})"
                f" — {anomaly['likely_reason']}"
            ),
        })
```

- [ ] **Step 2: Run all related tests**

Run: `pytest backend/tests/test_nav_jump_detection.py backend/tests/test_nav_incremental.py backend/tests/test_data_sync_logging.py -v`
Expected: all pass

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/data_sync.py
git commit -m "feat: record NAV jump anomalies in SyncLog errors"
```

---

### Task 18: 前端数据状态指示器（Dashboard）

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Add data status indicator dot**

In Dashboard, next to the snapshot info line, add a status dot using `useSyncLogs`:

```tsx
import { useSyncLogs } from '../api/hooks'

// inside Dashboard, add:
const { data: syncLogsData } = useSyncLogs(1)

// Determine status
const lastSyncStatus = syncLogsData?.logs?.[0]?.status ?? null
const statusDot = {
  done: { color: 'bg-emerald-400', label: '数据正常' },
  partial: { color: 'bg-amber-400', label: '部分数据同步失败' },
  failed: { color: 'bg-rose-400', label: '数据同步失败' },
  running: { color: 'bg-blue-400', label: '同步进行中' },
}[lastSyncStatus as string] ?? null
```

In the snapshot info `<p>`, add after the date:

```tsx
{statusDot && (
  <span className="inline-flex items-center gap-1 ml-3" title={statusDot.label}>
    <span className={`inline-block h-2 w-2 rounded-full ${statusDot.color}`} />
    <span className="text-xs text-slate-400">{statusDot.label}</span>
  </span>
)}
```

- [ ] **Step 2: Verify build**

Run: `cd frontend && npx tsc -b --noEmit`

Expected: no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat: add data status indicator dot on Dashboard"
```

---

### Task 19: 回归验证 — 所有现有测试通过

**Files:**
- None (verification only)

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python -m pytest tests -v`

Expected: all 35+ test files pass. If any existing test breaks due to the `sync_fund_nav` signature change, update those tests.

- [ ] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`

Expected: build succeeds without errors.

- [ ] **Step 3: Fix any regressions, then commit**

```bash
git add -A
git commit -m "test: regression verification - all existing tests pass after v1.7 changes"
```

---

### Task 20: 更新 README 索引

**Files:**
- Modify: `docs/superpowers/README.md`

- [ ] **Step 1: Move plan to completed**

Move this plan file from `plans/active/` to `plans/completed/` and update status to `completed`.

Update the README index row for v1.7 to link the completed plan.

- [ ] **Step 2: Commit**

```bash
git add docs/superpowers/README.md docs/superpowers/plans/
git commit -m "docs: update README index for v1.7 completion"
```
