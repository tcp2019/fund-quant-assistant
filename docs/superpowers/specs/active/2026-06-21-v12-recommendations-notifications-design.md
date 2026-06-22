# v1.2 候选基金推荐 + 基金搜索 + 浏览器通知 设计规格

> **Status:** active
> **Created:** 2026-06-21
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Parent spec:** [2026-06-21-fund-quant-assistant-design.md](./2026-06-21-fund-quant-assistant-design.md)

## 目标

在 v1.1 基础上交付 v1.2：**增配信号附带真实候选基金**、**导入时可靠基金搜索补代码**、**强信号浏览器通知**。所有面向用户的数据必须来自 akshare/东方财富公开接口或基于已入库真实净值计算，**禁止静态 seed、占位名或编造指标**。

## 真实数据红线

| 禁止 | 允许 |
|------|------|
| 硬编码候选基金代码池 | `fund_open_fund_rank_em` / `fund_money_rank_em` 排行 |
| 无来源的业绩数字 | 接口「近1年」字段，或 `FundNavHistory` 计算结果 |
| API 失败时用假数据凑数 | 空列表 + 明确错误/空态文案 |
| 搜索返回未收录基金 | `fund_name_em()` 全量目录（本地 catalog 缓存） |

每条对外展示的记录必须包含 **`data_source`** 与 **`as_of_date`**（数据截至日期）。

## 范围

### 包含（v1.2）

1. **M0**：sync 后基于真实 NAV 写入 `FundMetricsCache`（sharpe、max_drawdown、1y 收益等）
2. **M1**：`fund_catalog` 表 + `GET /api/funds/search` + Import 页搜索补代码
3. **M2**：`fund_rank_cache` + 候选推荐服务 + SignalsTable 展示候选（大类增配信号展开详情）
4. **M3**：Settings 通知开关 + sync 后强信号浏览器通知
5. **M4**：测试 + 文档

### 不包含

- akshare 以外的第三方数据源
- 静态 seed 候选池
- Service Worker / 后台推送 / 定时轮询通知
- 自动下单、持牌荐基话术

## 架构

### 数据流

```
akshare fund_name_em ──► fund_catalog (TTL 7d)
akshare fund_*_rank_em ──► fund_rank_cache (TTL 24h/category)
FundNavHistory ──► metrics 计算 ──► FundMetricsCache

增配 signal ──► recommend_funds_from_akshare ──► candidates[] on GET /api/signals
Import 缺代码 ──► GET /api/funds/search ──► 回填 fund_code/name
sync 成功 ──► GET /api/signals ──► (可选) Browser Notification
```

### 新增/变更数据模型

```
fund_catalog(code PK, name, fund_type, pinyin_abbr, synced_at)
fund_rank_cache(id, category, payload_json, fetched_at)
FundMetricsCache — 现有表，sync 时写入 computed_from="nav_history"
```

### API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/funds/search?q=&limit=` | 查 catalog，返回 code/name/fund_type |
| POST | `/api/funds/catalog/refresh` | 手动刷新 catalog（Settings） |
| GET | `/api/signals` | 增配信号附加 `candidates[]` |
| POST | `/api/data/sync` | 现有；增加 metrics 计算步骤 |

### 候选基金 Schema

```python
class FundCandidateOut(BaseModel):
    fund_code: str
    fund_name: str
    category: str
    return_1y: float | None      # akshare「近1年」，原样（百分比数值）
    return_1m: float | None = None  # akshare「近1月」（SignalsTable 候选优先展示）
    return_1w: float | None = None
    as_of_date: str               # akshare「日期」列
    data_source: str             # akshare_open_fund_rank | akshare_money_rank
```

### 大类 → akshare 数据源映射

| 内部 category | 数据源 | 过滤规则 | 排序 |
|---------------|--------|----------|------|
| stock | `fund_open_fund_rank_em` + catalog | 基金类型含 股票/混合/指数 | 近1年 ↓ |
| bond | 同上 | 基金类型含 债券 | 近1年 ↓ |
| money | `fund_money_rank_em` | — | 近1年 ↓ |
| qdii | open rank + catalog | 类型或名称含 QDII | 近1年 ↓ |
| gold | open rank + catalog | 名称含 黄金 | 近1年 ↓ |
| other | — | 无可靠映射 | 返回空 |

排除：当前持仓已有 `fund_code`；近1年为空/NaN 的条目。

### 基金搜索

- 数据源：`akshare.fund_name_em()`（约 2.7 万条）
- 刷新：启动时若 catalog 为空则拉取；Settings 提供「刷新基金目录」；默认 TTL 7 天
- 匹配：代码前缀或简称模糊包含 `q`
- 选中后可 lazy 调用现有 `sync_fund_metadata(code)`

### 浏览器通知

- 偏好：`localStorage.notificationsEnabled`，默认 false
- 权限：`Notification.requestPermission()` 于 Settings 开启时
- 触发：sync **成功** 后，存在 `strength >= 4` 且 `signal_type in (add, reduce)` 的真实信号
- 去重：同一 `snapshot_id` 仅通知一次（localStorage）
- 无强信号 / sync 失败 → 不通知

### 信号页 UI（SignalsTable）

v1.2 起信号页使用 `SignalsTable` 替代早期 `SignalCard`：

- 表格列：类型、标的、强度、得分、建议金额、原因摘要
- 类型筛选 tab：全部 / 减仓 / 增配 / 持有 / 观察
- 点击行展开详情；**大类增配**（`fund_code` 为空）展开区展示 `candidates[]`
- 限购降级（`purchase_limit` 层）在 `signalDisplay.signalActionType` 中映射为「观察」tab

### 合规文案

信号页候选区（展开大类增配详情）：

> 以下基金来自东方财富公开排行，按近 1 月收益排序（无则近 1 年），仅供参考，不构成投资建议。

## 错误处理

| 场景 | 行为 |
|------|------|
| akshare 排行失败 | `candidates=[]`，UI：「无法获取可靠排行，请稍后重试」 |
| catalog 未就绪 | 搜索 API 503 + 「基金目录同步中」 |
| 大类过滤后无结果 | 「该大类暂无公开排行数据」 |
| NAV 不足无法算指标 | 跳过该只 metrics，不展示虚假数字 |

## 测试策略

- 单元/集成：**pytest 中 mock akshare**（与 `test_data_sync` 一致）
- Fixture：使用录制的真实 akshare 响应 JSON（非 synthetic 编造）
- 生产路径：零 mock

## 分期

| 里程碑 | 内容 |
|--------|------|
| M0 | sync → FundMetricsCache |
| M1 | catalog + search + Import UI |
| M2 | rank cache + candidates + SignalsTable |
| M3 | browser notifications |
| M4 | 全量测试 + plan 归档 |

## Changelog

| 日期 | 作者 | 变更 |
|------|------|------|
| 2026-06-21 | Agent + User | 初始版本；用户确认：近1年排序、catalog 每周+手动刷新、M0–M4 整包 |
| 2026-06-21 | Agent | 已实现并交付 |
| 2026-06-22 | Agent | 文档同步：SignalCard → SignalsTable；候选 Schema 补充 return_1m/1w |
