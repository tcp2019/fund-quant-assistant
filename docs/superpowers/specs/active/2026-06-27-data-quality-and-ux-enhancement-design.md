# v1.7 数据质量与体验增强 设计规格

> **Status:** active
> **Created:** 2026-06-27
> **Supersedes:** (none)
> **Superseded by:** (none)

## 目标

修复数据同步静默失败、前端重复请求、NAV 全量拉取三大痛点，增加净值跳变检测，提升系统的数据可靠性和用户体验。

## 范围

### 包含

1. **数据同步失败告警** — SyncLog 表 + API + 前端同步历史和状态指示器
2. **前端 TanStack Query 重构** — 替换 7 个页面的手动 fetch，获得缓存/去重/后台刷新
3. **NAV 同步增量化** — sync_fund_nav 从全量拉取改为增量拉取
4. **NAV 跳变检测** — 写入前检测日涨跌超 15% 的异常点，记录到 sync_log

### 不包含

- Phase 2 信号引擎增强（风格因子、宏观感知、动态权重）
- Alembic 数据库迁移
- 多数据源（tushare/joinquant）接入
- 模拟调仓、新手引导、移动端适配

## 架构

### 后端

新增 `SyncLog` 表：

```python
class SyncLog(SQLModel, table=True):
    id: int
    started_at: datetime
    finished_at: datetime | None
    status: str  # "running" | "done" | "partial" | "failed"
    total_funds: int
    success_funds: int
    failed_funds: int
    errors_json: str  # [{"fund_code": "xxx", "stage": "nav", "error": "..."}]
```

`sync_portfolio_funds()` 重构：每个基金的 metadata / nav / purchase_limit 同步改为逐个 try/except，成功+1 失败记录到 errors_json，最终写入 SyncLog。不再静默吞异常。

新增 API：`GET /api/settings/sync-logs?limit=3` 返回最近 N 条日志。

`sync_fund_nav(code, since_date=None)` 增量逻辑：
- 查询 `FundNavHistory` 表中该 code 的最大 date
- 有 → since_date = max_date，只拉取之后的数据
- 无 → 全量拉取

NAV 跳变检测 `detect_nav_jump(navs)` 在写入前运行，阈值 15%，异常记录推入 sync_log.errors_json。

### 前端

新增依赖 `@tanstack/react-query`。

文件结构：
```
frontend/src/api/
├── client.ts        ← 保留
├── queries.ts       ← 🆕 query keys 常量 + query/mutation functions
└── hooks.ts         ← 🆕 useOverview, useSignals, useOpportunities 等
```

`App.tsx` 包裹 `QueryClientProvider`，配置：
- `staleTime: 5 * 60 * 1000`（5分钟）
- `refetchOnWindowFocus: false`

7 个页面改造模式：
```
// Before
const [data, setData] = useState(null)
useEffect(() => { fetch().then(setData) }, [])

// After
const { data } = useOverview()
```

同步 mutation 成功后 `invalidateQueries` 相关 query。

Settings 页底部新增「同步历史」区域（表格展示最近 3 次），Dashboard 快照时间旁增加数据状态圆点指示器。

## 错误处理

- SyncLog 写入失败不影响主同步流程（log 失败但数据同步继续）
- TanStack Query 的 `onError` 在 hook 层统一处理，页面组件只消费 `isError` / `error`
- NAV 跳变检测结果是 advisory 的（记录但不拒绝写入）
- 增量同步首次失败时自动回退到全量同步

## 测试策略

- `test_sync_log.py` — 验证 SyncLog 增删查、各状态正确记录
- `test_nav_incremental.py` — 验证增量同步只拉取新日期
- `test_nav_jump_detection.py` — 正常净值、分红跳变、数据异常等场景
- 前端 — 现有页面功能不变，手动验证 query hooks 替换后数据展示一致
- 现有 35 个测试文件全部保持通过

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-27 | tcp | 初始版本 |
