# 基金量化助手 v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

> **Status:** completed
> **Created:** 2026-06-21
> **Spec:** docs/superpowers/specs/active/2026-06-21-fund-quant-assistant-design.md
> **Supersedes:** (none)
> **Superseded by:** (none)
> **Based on:** (none)

**Goal:** 交付 v1 个人基金量化助手：截图 OCR 导入持仓、Dashboard 概览、akshare 数据同步、三层量化信号引擎与 Web UI。

**Architecture:** React SPA 通过 REST 调用 FastAPI；SQLite 存快照/持仓/信号；业务逻辑分层为 repository → service → API；信号引擎纯函数、可单测；OCR 按 App 分 parser，先文本 fixture 测通再接入 PaddleOCR。

**Tech Stack:** Python 3.11+, FastAPI, SQLModel, SQLite, pytest, akshare, PaddleOCR | React 18, Vite, TypeScript, Tailwind, Recharts

---

## 文件结构（全项目）

```
fund-quant-assistant/
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── models.py
│   │   ├── schemas/
│   │   │   ├── portfolio.py
│   │   │   ├── ocr.py
│   │   │   ├── signals.py
│   │   │   └── settings.py
│   │   ├── repositories/
│   │   │   └── portfolio.py
│   │   ├── services/
│   │   │   ├── ocr/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── pipeline.py
│   │   │   │   └── parsers/
│   │   │   │       ├── base.py
│   │   │   │       ├── alipay.py
│   │   │   │       ├── tiantian.py
│   │   │   │       └── licaitong.py
│   │   │   ├── data_sync.py
│   │   │   ├── metrics.py
│   │   │   ├── fund_classifier.py
│   │   │   └── signals/
│   │   │       ├── engine.py
│   │   │       ├── rebalance.py
│   │   │       ├── concentration.py
│   │   │       └── performance.py
│   │   └── api/
│   │       ├── deps.py
│   │       └── routes/
│   │           ├── ocr.py
│   │           ├── portfolio.py
│   │           ├── signals.py
│   │           ├── analysis.py
│   │           ├── data.py
│   │           └── settings.py
│   └── tests/
│       ├── conftest.py
│       ├── fixtures/
│       │   └── ocr/
│       │       ├── alipay_sample.txt
│       │       ├── tiantian_sample.txt
│       │       └── licaitong_sample.txt
│       ├── test_metrics.py
│       ├── test_ocr_parsers.py
│       ├── test_signals_rebalance.py
│       ├── test_signals_concentration.py
│       ├── test_signals_engine.py
│       └── test_api_portfolio.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api/client.ts
│       ├── types/index.ts
│       ├── components/
│       │   ├── Layout.tsx
│       │   ├── StatCard.tsx
│       │   ├── HoldingsTable.tsx
│       │   ├── SignalCard.tsx
│       │   └── AllocationChart.tsx
│       └── pages/
│           ├── Dashboard.tsx
│           ├── ImportPage.tsx
│           ├── HoldingsPage.tsx
│           ├── SignalsPage.tsx
│           ├── AnalysisPage.tsx
│           └── SettingsPage.tsx
├── README.md
└── docs/superpowers/...
```

---

## M1：骨架 + OCR + 持仓 + 概览

### Task 1: Backend 项目骨架

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/tests/conftest.py`

- [x] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "fund-quant-assistant"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115.0",
  "uvicorn[standard]>=0.32.0",
  "sqlmodel>=0.0.22",
  "pydantic-settings>=2.6.0",
  "python-multipart>=0.0.12",
  "akshare>=1.14.0",
  "httpx>=0.27.0",
  "numpy>=2.0.0",
  "pandas>=2.2.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.3.0", "pytest-asyncio>=0.24.0", "httpx>=0.27.0"]
ocr = ["paddleocr>=2.9.0", "paddlepaddle>=3.0.0"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [x] **Step 2: 创建 config 与 main**

`backend/app/config.py`:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./fund_quant.db"
    upload_dir: str = "./uploads"
    cors_origins: list[str] = ["http://localhost:5173"]

    class Config:
        env_file = ".env"


settings = Settings()
```

`backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

app = FastAPI(title="Fund Quant Assistant", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

- [x] **Step 3: 写 health 测试**

`backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

- [x] **Step 4: 安装依赖并跑测试**

Run:
```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/test_health.py -v
```
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add backend/
git commit -m "chore: bootstrap FastAPI backend with health check"
```

---

### Task 2: 数据库模型与初始化

**Files:**
- Create: `backend/app/db/session.py`
- Create: `backend/app/db/models.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_db_models.py`

- [x] **Step 1: 写 failing test — 创建 snapshot 与 holding**

`backend/tests/test_db_models.py`:

```python
from sqlmodel import Session, select

from app.db.models import Holding, PortfolioSnapshot
from app.db.session import create_db_and_tables, engine


def test_create_snapshot_with_holdings():
    create_db_and_tables()
    with Session(engine) as session:
        snap = PortfolioSnapshot(source="manual", note="test")
        session.add(snap)
        session.commit()
        session.refresh(snap)

        holding = Holding(
            snapshot_id=snap.id,
            fund_code="110011",
            fund_name="易方达优质精选",
            shares=1000.0,
            cost_price=1.5,
            market_value=1800.0,
            profit=300.0,
            profit_rate=0.2,
            platform="alipay",
        )
        session.add(holding)
        session.commit()

        rows = session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
        assert len(rows) == 1
        assert rows[0].fund_code == "110011"
```

- [x] **Step 2: 跑测试确认 FAIL**

Run: `pytest tests/test_db_models.py -v`
Expected: FAIL — models not defined

- [x] **Step 3: 实现 models 与 session**

`backend/app/db/models.py`:

```python
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class PortfolioSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = "ocr"
    note: str = ""


class Holding(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    snapshot_id: int = Field(foreign_key="portfoliosnapshot.id", index=True)
    fund_code: str = Field(index=True)
    fund_name: str
    shares: float
    cost_price: float
    market_value: float
    profit: float = 0.0
    profit_rate: float = 0.0
    platform: str = "unknown"
    hold_days: Optional[int] = None


class OcrJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = "pending"  # pending | parsed | confirmed | failed
    image_paths: str = "[]"  # JSON array string
    parsed_json: str = "{}"
    confirmed_at: Optional[datetime] = None


class FundMetadata(SQLModel, table=True):
    code: str = Field(primary_key=True)
    name: str
    fund_type: str = "other"
    category: str = "other"
    benchmark_code: str = ""
    manager: str = ""


class FundNavHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True)
    date: str = Field(index=True)
    nav: float
    acc_nav: float = 0.0


class FundMetricsCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True)
    as_of_date: str
    sharpe_1y: Optional[float] = None
    max_drawdown_1y: Optional[float] = None
    excess_return_1y: Optional[float] = None


class StrategyConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    template_name: str = "balanced"
    target_weights_json: str = "{}"
    thresholds_json: str = "{}"


class SignalRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    snapshot_id: int = Field(index=True)
    fund_code: str = ""
    signal_type: str  # reduce | add | hold | watch
    score: float
    strength: int
    reasons_json: str = "[]"
    suggested_amount: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

`backend/app/db/session.py`:

```python
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
```

- [x] **Step 4: 在 startup 注册建表**

在 `backend/app/main.py` 追加:

```python
from contextlib import asynccontextmanager

from app.db.session import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Fund Quant Assistant", version="0.1.0", lifespan=lifespan)
```

- [x] **Step 5: 跑测试**

Run: `pytest tests/test_db_models.py -v`
Expected: PASS

- [x] **Step 6: Commit**

```bash
git add backend/app/db/ backend/app/main.py backend/tests/test_db_models.py
git commit -m "feat: add SQLModel schema for portfolio and signals"
```

---

### Task 3: Portfolio Repository 与概览 API

**Files:**
- Create: `backend/app/schemas/portfolio.py`
- Create: `backend/app/repositories/portfolio.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/routes/portfolio.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api_portfolio.py`

- [x] **Step 1: 写 failing API test**

`backend/tests/test_api_portfolio.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_overview_empty():
    resp = client.get("/api/portfolio/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_value"] == 0
    assert data["holdings"] == []


def test_create_snapshot_and_overview():
    payload = {
        "holdings": [
            {
                "fund_code": "110011",
                "fund_name": "易方达优质精选",
                "shares": 1000,
                "cost_price": 1.5,
                "market_value": 1800,
                "profit": 300,
                "profit_rate": 0.2,
                "platform": "alipay",
            }
        ],
        "source": "manual",
    }
    resp = client.post("/api/portfolio/snapshots", json=payload)
    assert resp.status_code == 201

    overview = client.get("/api/portfolio/overview").json()
    assert overview["total_value"] == 1800
    assert overview["total_cost"] == 1500
    assert overview["total_profit"] == 300
    assert len(overview["holdings"]) == 1
    assert overview["holdings"][0]["weight_pct"] == 100.0
```

- [x] **Step 2: 跑测试确认 FAIL**

Run: `pytest tests/test_api_portfolio.py -v`

- [x] **Step 3: 实现 schemas + repository + routes**

`backend/app/schemas/portfolio.py`:

```python
from pydantic import BaseModel


class HoldingIn(BaseModel):
    fund_code: str
    fund_name: str
    shares: float
    cost_price: float
    market_value: float
    profit: float = 0.0
    profit_rate: float = 0.0
    platform: str = "unknown"
    hold_days: int | None = None


class SnapshotCreate(BaseModel):
    holdings: list[HoldingIn]
    source: str = "manual"
    note: str = ""


class HoldingOut(HoldingIn):
    weight_pct: float


class OverviewOut(BaseModel):
    snapshot_id: int | None
    total_value: float
    total_cost: float
    total_profit: float
    total_profit_rate: float
    holdings: list[HoldingOut]
```

`backend/app/repositories/portfolio.py`:

```python
from sqlmodel import Session, select

from app.db.models import Holding, PortfolioSnapshot
from app.schemas.portfolio import HoldingIn, OverviewOut, SnapshotCreate


def get_latest_snapshot(session: Session) -> PortfolioSnapshot | None:
    return session.exec(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.created_at.desc())
    ).first()


def create_snapshot(session: Session, data: SnapshotCreate) -> PortfolioSnapshot:
    snap = PortfolioSnapshot(source=data.source, note=data.note)
    session.add(snap)
    session.commit()
    session.refresh(snap)

    merged: dict[str, HoldingIn] = {}
    for h in data.holdings:
        if h.fund_code in merged:
            existing = merged[h.fund_code]
            merged[h.fund_code] = HoldingIn(
                fund_code=h.fund_code,
                fund_name=h.fund_name,
                shares=existing.shares + h.shares,
                cost_price=(existing.cost_price * existing.shares + h.cost_price * h.shares)
                / (existing.shares + h.shares),
                market_value=existing.market_value + h.market_value,
                profit=existing.profit + h.profit,
                profit_rate=0.0,
                platform=f"{existing.platform},{h.platform}",
            )
        else:
            merged[h.fund_code] = h

    for h in merged.values():
        session.add(
            Holding(
                snapshot_id=snap.id,
                fund_code=h.fund_code,
                fund_name=h.fund_name,
                shares=h.shares,
                cost_price=h.cost_price,
                market_value=h.market_value,
                profit=h.profit,
                profit_rate=h.profit_rate,
                platform=h.platform,
                hold_days=h.hold_days,
            )
        )
    session.commit()
    return snap


def build_overview(session: Session) -> OverviewOut:
    snap = get_latest_snapshot(session)
    if not snap:
        return OverviewOut(
            snapshot_id=None,
            total_value=0,
            total_cost=0,
            total_profit=0,
            total_profit_rate=0,
            holdings=[],
        )

    holdings = session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
    total_value = sum(h.market_value for h in holdings)
    total_cost = sum(h.shares * h.cost_price for h in holdings)
    total_profit = sum(h.profit for h in holdings)
    total_profit_rate = (total_profit / total_cost) if total_cost else 0.0

    out_holdings = []
    for h in holdings:
        weight = (h.market_value / total_value * 100) if total_value else 0.0
        out_holdings.append(
            {
                "fund_code": h.fund_code,
                "fund_name": h.fund_name,
                "shares": h.shares,
                "cost_price": h.cost_price,
                "market_value": h.market_value,
                "profit": h.profit,
                "profit_rate": h.profit_rate,
                "platform": h.platform,
                "hold_days": h.hold_days,
                "weight_pct": round(weight, 2),
            }
        )

    return OverviewOut(
        snapshot_id=snap.id,
        total_value=round(total_value, 2),
        total_cost=round(total_cost, 2),
        total_profit=round(total_profit, 2),
        total_profit_rate=round(total_profit_rate, 4),
        holdings=out_holdings,
    )
```

`backend/app/api/deps.py`:

```python
from collections.abc import Generator

from sqlmodel import Session

from app.db.session import engine


def get_db() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
```

`backend/app/api/routes/portfolio.py`:

```python
from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_db
from app.repositories import portfolio as repo
from app.schemas.portfolio import OverviewOut, SnapshotCreate

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/overview", response_model=OverviewOut)
def overview(session: Session = Depends(get_db)):
    return repo.build_overview(session)


@router.get("/holdings", response_model=OverviewOut)
def holdings(session: Session = Depends(get_db)):
    return repo.build_overview(session)


@router.post("/snapshots", status_code=201)
def create_snapshot(data: SnapshotCreate, session: Session = Depends(get_db)):
    snap = repo.create_snapshot(session, data)
    return {"snapshot_id": snap.id}
```

在 `main.py` 注册: `from app.api.routes.portfolio import router as portfolio_router` → `app.include_router(portfolio_router)`

- [x] **Step 4: 跑测试 PASS**

- [x] **Step 5: Commit**

```bash
git commit -m "feat: portfolio snapshot CRUD and overview API"
```

---

### Task 4: OCR 文本 Parser（fixture 驱动，暂不依赖 Paddle）

**Files:**
- Create: `backend/app/services/ocr/parsers/base.py`
- Create: `backend/app/services/ocr/parsers/alipay.py`
- Create: `backend/app/services/ocr/parsers/tiantian.py`
- Create: `backend/app/services/ocr/parsers/licaitong.py`
- Create: `backend/app/services/ocr/pipeline.py`
- Create: `backend/tests/fixtures/ocr/*.txt`
- Test: `backend/tests/test_ocr_parsers.py`

- [x] **Step 1: 添加 fixture 样本文本**

`backend/tests/fixtures/ocr/alipay_sample.txt`:

```
我的基金
易方达优质精选混合 110011
持有份额 1000.00
成本价 1.5000
持有市值 1800.00
持有收益 +300.00
收益率 +20.00%
```

`backend/tests/fixtures/ocr/tiantian_sample.txt`:

```
基金持仓
110011 易方达优质精选混合
份额:1000 成本:1.5 市值:1800 收益:300 收益率:20%
```

- [x] **Step 2: 写 failing parser test**

`backend/tests/test_ocr_parsers.py`:

```python
from pathlib import Path

from app.services.ocr.parsers.alipay import parse_alipay_text
from app.services.ocr.parsers.tiantian import parse_tiantian_text

FIXTURES = Path(__file__).parent / "fixtures" / "ocr"


def test_parse_alipay():
    text = (FIXTURES / "alipay_sample.txt").read_text(encoding="utf-8")
    rows = parse_alipay_text(text)
    assert len(rows) == 1
    assert rows[0].fund_code == "110011"
    assert rows[0].shares == 1000.0
    assert rows[0].market_value == 1800.0


def test_parse_tiantian():
    text = (FIXTURES / "tiantian_sample.txt").read_text(encoding="utf-8")
    rows = parse_tiantian_text(text)
    assert rows[0].fund_code == "110011"
    assert rows[0].cost_price == 1.5
```

- [x] **Step 3: 实现 base + parsers**

`backend/app/services/ocr/parsers/base.py`:

```python
import re
from dataclasses import dataclass


@dataclass
class ParsedHolding:
    fund_code: str
    fund_name: str
    shares: float
    cost_price: float
    market_value: float
    profit: float
    profit_rate: float
    platform: str
    confidence: float = 1.0


def extract_fund_code(text: str) -> str | None:
    m = re.search(r"\b(\d{6})\b", text)
    return m.group(1) if m else None


def extract_float(label_patterns: list[str], text: str) -> float | None:
    for pat in label_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(",", ""))
    return None
```

`backend/app/services/ocr/parsers/alipay.py`:

```python
import re

from app.services.ocr.parsers.base import ParsedHolding, extract_float, extract_fund_code


def parse_alipay_text(text: str) -> list[ParsedHolding]:
    blocks = re.split(r"\n\s*\n", text.strip())
    results: list[ParsedHolding] = []
    for block in blocks:
        code = extract_fund_code(block)
        if not code:
            continue
        name_match = re.search(r"([\u4e00-\u9fffA-Za-z0-9]+)\s+" + code, block)
        name = name_match.group(1) if name_match else ""
        shares = extract_float([r"持有份额\s*([\d.]+)", r"份额\s*([\d.]+)"], block) or 0.0
        cost = extract_float([r"成本价\s*([\d.]+)"], block) or 0.0
        mv = extract_float([r"持有市值\s*([\d.]+)", r"市值\s*([\d.]+)"], block) or 0.0
        profit = extract_float([r"持有收益\s*\+?([\d.]+)"], block) or 0.0
        rate = extract_float([r"收益率\s*\+?([\d.]+)%"], block) or 0.0
        results.append(
            ParsedHolding(
                fund_code=code,
                fund_name=name,
                shares=shares,
                cost_price=cost,
                market_value=mv,
                profit=profit,
                profit_rate=rate / 100,
                platform="alipay",
            )
        )
    return results
```

`backend/app/services/ocr/parsers/tiantian.py`:

```python
import re

from app.services.ocr.parsers.base import ParsedHolding


def parse_tiantian_text(text: str) -> list[ParsedHolding]:
    for line in text.splitlines():
        m = re.search(
            r"(\d{6})\s+([\u4e00-\u9fff\w]+).*?份额[:：]?\s*([\d.]+).*?成本[:：]?\s*([\d.]+).*?市值[:：]?\s*([\d.]+).*?收益[:：]?\s*([\d.]+).*?收益率[:：]?\s*([\d.]+)%",
            line,
        )
        if m:
            return [
                ParsedHolding(
                    fund_code=m.group(1),
                    fund_name=m.group(2),
                    shares=float(m.group(3)),
                    cost_price=float(m.group(4)),
                    market_value=float(m.group(5)),
                    profit=float(m.group(6)),
                    profit_rate=float(m.group(7)) / 100,
                    platform="tiantian",
                )
            ]
    return []
```

`licaitong.py` 结构同 alipay，platform=`licaitong`。

- [x] **Step 4: 跑测试 PASS**

- [x] **Step 5: Commit**

```bash
git commit -m "feat: OCR text parsers for alipay and tiantian fixtures"
```

---

### Task 5: OCR Upload API + Confirm 流程

**Files:**
- Create: `backend/app/schemas/ocr.py`
- Create: `backend/app/api/routes/ocr.py`
- Modify: `backend/app/services/ocr/pipeline.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_api_ocr.py`

- [x] **Step 1: pipeline 自动检测 platform**

`backend/app/services/ocr/pipeline.py`:

```python
from app.services.ocr.parsers.alipay import parse_alipay_text
from app.services.ocr.parsers.licaitong import parse_licaitong_text
from app.services.ocr.parsers.tiantian import parse_tiantian_text
from app.services.ocr.parsers.base import ParsedHolding


def parse_ocr_text(text: str, platform_hint: str | None = None) -> list[ParsedHolding]:
    parsers = {
        "alipay": parse_alipay_text,
        "tiantian": parse_tiantian_text,
        "licaitong": parse_licaitong_text,
    }
    if platform_hint and platform_hint in parsers:
        return parsers[platform_hint](text)

    for name, fn in parsers.items():
        rows = fn(text)
        if rows:
            return rows
    return []


def validate_holding(row: ParsedHolding) -> list[str]:
    warnings: list[str] = []
    if row.shares <= 0 or row.market_value <= 0:
        warnings.append(f"{row.fund_code}: 份额或市值无效")
    implied_nav = row.market_value / row.shares if row.shares else 0
    if row.cost_price > 0 and abs(implied_nav - row.cost_price) / row.cost_price > 0.5:
        warnings.append(f"{row.fund_code}: 市值/份额与成本价偏差较大，请核对")
    return warnings
```

- [x] **Step 2: OCR routes**

`POST /api/ocr/upload` 接受 `platform` + `text`（v1 先用文本字段联调；图片 OCR 在 Task 5b 接 PaddleOCR）
`POST /api/ocr/{job_id}/confirm` 将 parsed holdings 写入 snapshot

- [x] **Step 3: API test — upload + confirm**

```python
def test_ocr_upload_and_confirm():
    upload = client.post(
        "/api/ocr/upload",
        json={"platform": "alipay", "text": (FIXTURES / "alipay_sample.txt").read_text()},
    )
    assert upload.status_code == 200
    job_id = upload.json()["job_id"]
    assert len(upload.json()["holdings"]) == 1

    confirm = client.post(f"/api/ocr/{job_id}/confirm", json={"holdings": upload.json()["holdings"]})
    assert confirm.status_code == 201

    overview = client.get("/api/portfolio/overview").json()
    assert overview["total_value"] == 1800
```

- [x] **Step 4: 实现并 PASS**

- [x] **Step 5: Commit**

---

### Task 5b: PaddleOCR 图片上传（可选依赖）

**Files:**
- Modify: `backend/app/api/routes/ocr.py`
- Modify: `backend/app/services/ocr/pipeline.py`

- [x] **Step 1: 增加 `run_paddle_ocr(image_path: str) -> str`**，lazy import paddleocr
- [x] **Step 2: `POST /api/ocr/upload` 支持 `UploadFile`**，保存到 `upload_dir`，OCR 后走同一 parser
- [x] **Step 3: 无 paddle 环境时返回 501 + 提示用文本模式**
- [x] **Step 4: Commit**

---

### Task 6: Frontend 骨架与 Dashboard

**Files:**
- Create: `frontend/` via `npm create vite@latest frontend -- --template react-ts`
- Create: `frontend/src/api/client.ts`, pages, components
- Modify: `frontend/vite.config.ts` proxy `/api` → `localhost:8000`

- [x] **Step 1: 初始化 Vite + Tailwind**

Run:
```bash
cd frontend && npm install && npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
npm install recharts react-router-dom
```

`frontend/vite.config.ts` 加 proxy:
```typescript
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
```

- [x] **Step 2: Layout + 路由**

`frontend/src/App.tsx` 路由: `/`, `/import`, `/holdings`, `/signals`, `/analysis`, `/settings`

- [x] **Step 3: Dashboard 拉 overview**

`frontend/src/pages/Dashboard.tsx` 调用 `GET /api/portfolio/overview`，展示 StatCard（总市值/总盈亏）+ HoldingsTable；空状态引导 `/import`

- [x] **Step 4: 手动验证**

Run backend: `uvicorn app.main:app --reload --app-dir backend`
Run frontend: `npm run dev`
Expected: 空 Dashboard 显示导入引导

- [x] **Step 5: Commit**

```bash
git commit -m "feat: React dashboard with portfolio overview"
```

---

### Task 7: Import 页（上传 + 确认）

**Files:**
- Create: `frontend/src/pages/ImportPage.tsx`

- [x] **Step 1: 表单 — platform 选择 + 文本粘贴区（v1 联调）+ 文件上传**
- [x] **Step 2: 调用 upload API，展示可编辑表格**
- [x] **Step 3: Confirm 后跳转 Dashboard**
- [x] **Step 4: Commit**

---

## M2：数据同步 + 指标 + 再平衡信号

### Task 8: Fund Classifier 与 Data Sync

**Files:**
- Create: `backend/app/services/fund_classifier.py`
- Create: `backend/app/services/data_sync.py`
- Create: `backend/app/api/routes/data.py`
- Test: `backend/tests/test_data_sync.py`（mock akshare）

- [x] **Step 1: fund_classifier — 按名称/类型映射大类**

```python
CATEGORY_RULES = [
    ("债券", "bond"),
    ("货币", "money"),
    ("QDII", "qdii"),
    ("黄金", "gold"),
    ("混合", "stock"),
    ("股票", "stock"),
    ("指数", "stock"),
]


def classify_fund(name: str, fund_type: str = "") -> str:
    text = name + fund_type
    for keyword, cat in CATEGORY_RULES:
        if keyword in text:
            return cat
    return "other"
```

- [x] **Step 2: data_sync.sync_fund_nav(code) — mock 测试**

```python
def test_sync_fund_nav_mock(monkeypatch):
    def fake_fetch(code: str):
        return [{"date": "2025-06-01", "nav": 1.8, "acc_nav": 1.8}]

    monkeypatch.setattr("app.services.data_sync.fetch_nav_from_akshare", fake_fetch)
    # assert rows inserted into FundNavHistory
```

- [x] **Step 3: 实现 akshare 拉取 + 重试 3 次**
- [x] **Step 4: `POST /api/data/sync` 同步当前持仓所有 code**
- [x] **Step 5: Commit**

---

### Task 9: Metrics 计算器

**Files:**
- Create: `backend/app/services/metrics.py`
- Test: `backend/tests/test_metrics.py`

- [x] **Step 1: failing tests**

```python
import numpy as np
from app.services.metrics import max_drawdown, sharpe_ratio, correlation_matrix


def test_max_drawdown():
    returns = np.array([0.1, -0.05, -0.2, 0.15])
    assert round(max_drawdown(returns), 4) == round(-0.24, 4)


def test_sharpe_ratio():
    returns = np.array([0.01, 0.02, -0.01, 0.015, 0.005])
    s = sharpe_ratio(returns, risk_free=0.0)
    assert s > 0


def test_correlation_matrix():
    a = np.array([0.01, 0.02, -0.01, 0.03])
    b = np.array([0.015, 0.01, -0.005, 0.02])
    corr = correlation_matrix([a, b])
    assert corr.shape == (2, 2)
    assert corr[0, 0] == 1.0
```

- [x] **Step 2: 实现**

```python
import numpy as np


def max_drawdown(returns: np.ndarray) -> float:
    cumulative = np.cumprod(1 + returns)
    peak = np.maximum.accumulate(cumulative)
    dd = cumulative / peak - 1
    return float(dd.min())


def sharpe_ratio(returns: np.ndarray, risk_free: float = 0.0, periods: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    excess = returns - risk_free / periods
    std = excess.std(ddof=1)
    if std == 0:
        return 0.0
    return float(excess.mean() / std * np.sqrt(periods))


def correlation_matrix(series_list: list[np.ndarray]) -> np.ndarray:
    if not series_list:
        return np.array([[]])
    mat = np.column_stack(series_list)
    return np.corrcoef(mat, rowvar=False)
```

- [x] **Step 3: PASS + Commit**

---

### Task 10: 再平衡信号层

**Files:**
- Create: `backend/app/services/signals/rebalance.py`
- Create: `backend/app/schemas/settings.py`（默认模板）
- Test: `backend/tests/test_signals_rebalance.py`

- [x] **Step 1: 默认策略配置**

```python
DEFAULT_TEMPLATES = {
    "balanced": {
        "stock": 0.40,
        "bond": 0.30,
        "money": 0.15,
        "qdii": 0.10,
        "other": 0.05,
    },
    "conservative": {"stock": 0.20, "bond": 0.50, "money": 0.20, "qdii": 0.05, "other": 0.05},
    "aggressive": {"stock": 0.60, "bond": 0.15, "money": 0.05, "qdii": 0.15, "other": 0.05},
}

DEFAULT_THRESHOLDS = {
    "rebalance_deviation_pct": 5.0,
    "rebalance_force_days": 365,
    "single_fund_max_pct": 25.0,
    "correlation_max": 0.85,
}
```

- [x] **Step 2: failing test**

```python
from app.services.signals.rebalance import compute_rebalance_signals


def test_rebalance_underweight_bond():
    category_weights = {"stock": 0.50, "bond": 0.20, "money": 0.15, "qdii": 0.10, "other": 0.05}
    target = DEFAULT_TEMPLATES["balanced"]
    signals = compute_rebalance_signals(category_weights, target, total_value=10000, threshold_pct=5.0)
    bond_signal = next(s for s in signals if s["category"] == "bond")
    assert bond_signal["signal_type"] == "add"
    assert bond_signal["deviation_pct"] == 10.0
    assert bond_signal["suggested_amount"] == 1000.0
```

- [x] **Step 3: 实现 compute_rebalance_signals**
- [x] **Step 4: PASS + Commit**

---

## M3：集中度 + 业绩信号 + 信号面板

### Task 11: 集中度信号层

**Files:**
- Create: `backend/app/services/signals/concentration.py`
- Test: `backend/tests/test_signals_concentration.py`

- [x] **Step 1: test — 单只 >25% 触发 reduce**

```python
def test_single_fund_concentration():
    holdings = [{"fund_code": "110011", "weight_pct": 30.0, "hold_days": 30}]
    signals = compute_concentration_signals(holdings, corr_matrix=None, thresholds=DEFAULT_THRESHOLDS)
    assert signals[0]["signal_type"] == "reduce"
    assert "25%" in signals[0]["detail"]
```

- [x] **Step 2: test — hold_days < 7 阻止卖出**

- [x] **Step 3: test — 高相关 pair >0.85**

- [x] **Step 4: 实现 + Commit**

---

### Task 12: 业绩质量信号层

**Files:**
- Create: `backend/app/services/signals/performance.py`
- Test: 在 `test_signals_engine.py` 中 mock metrics cache

- [x] **Step 1: test — excess_return_1y < -5% → watch/reduce**

```python
def test_underperform_benchmark():
    metrics = {"110011": {"excess_return_1y": -0.08, "sharpe_1y": 0.5, "max_drawdown_1y": -0.25}}
    signals = compute_performance_signals(["110011"], metrics)
    assert signals[0]["signal_type"] in ("watch", "reduce")
```

- [x] **Step 2: 实现 + Commit**

---

### Task 13: 信号聚合引擎 + API

**Files:**
- Create: `backend/app/services/signals/engine.py`
- Create: `backend/app/api/routes/signals.py`
- Test: `backend/tests/test_signals_engine.py`

- [x] **Step 1: SignalEngine 合并三层，权重 40/30/30**

```python
LAYER_WEIGHTS = {"rebalance": 0.4, "concentration": 0.3, "performance": 0.3}


def aggregate_signals(rebalance, concentration, performance) -> list[dict]:
    # 合并 score: -100~100, strength 1~5, reasons_json
    ...
```

- [x] **Step 2: `run_signal_engine(session)` — 读最新 snapshot → 写 SignalRecord**
- [x] **Step 3: `GET /api/signals` 按 score 排序**
- [x] **Step 4: data sync 完成后自动 trigger engine**
- [x] **Step 5: Commit**

---

### Task 14: Signals 前端页

**Files:**
- Create: `frontend/src/pages/SignalsPage.tsx`
- Create: `frontend/src/components/SignalCard.tsx`

- [x] **Step 1: 列表展示 signal_type / strength / reasons / suggested_amount**
- [x] **Step 2: 顶部免责声明 banner**
- [x] **Step 3: 空状态 — 先导入持仓再 sync**
- [x] **Step 4: Commit**

---

### Task 15: Analysis 页（相关性 + 风险）

**Files:**
- Create: `backend/app/api/routes/analysis.py`
- Create: `frontend/src/pages/AnalysisPage.tsx`

- [x] **Step 1: `GET /api/analysis/correlation` 返回 matrix + labels**
- [x] **Step 2: `GET /api/analysis/risk` 返回 volatility, sharpe, max_dd**
- [x] **Step 3: 前端热力图 + 指标卡片**
- [x] **Step 4: Commit**

---

## M4：策略设置 + 快照历史 + Polish

### Task 16: Settings API + UI

**Files:**
- Create: `backend/app/api/routes/settings.py`
- Create: `frontend/src/pages/SettingsPage.tsx`

- [x] **Step 1: `GET/PUT /api/settings/strategy` — template + custom weights + thresholds**
- [x] **Step 2: UI — 模板下拉 + 阈值 slider**
- [x] **Step 3: 保存后 re-run signal engine**
- [x] **Step 4: Commit**

---

### Task 17: 快照历史

**Files:**
- Modify: `backend/app/api/routes/portfolio.py`
- Modify: `frontend/src/pages/HoldingsPage.tsx`

- [x] **Step 1: `GET /api/portfolio/snapshots` 列表**
- [x] **Step 2: Holdings 页展示历史 + 对比 total_value 变化**
- [x] **Step 3: Commit**

---

### Task 18: README 与启动脚本

**Files:**
- Create: `README.md`
- Create: `scripts/dev.sh`

- [x] **Step 1: README 含安装、启动、免责声明**
- [x] **Step 2: dev.sh 同时起 backend + frontend**
- [x] **Step 3: Commit**

---

### Task 19: 全量测试与验收

- [x] **Step 1: `pytest backend/tests -v` 全绿**
- [x] **Step 2: 手动验收路径：导入 fixture → sync → 查看 signals → 改 settings → 信号变化**
- [x] **Step 3: 确认 spec 非功能需求：同输入同输出可复现**

---

## Spec 覆盖自检

| Spec 需求 | 对应 Task |
|-----------|-----------|
| OCR 三平台导入 | Task 4, 5, 5b, 7 |
| 人工确认 | Task 5, 7 |
| Dashboard 概览 | Task 3, 6 |
| akshare 同步 | Task 8 |
| 三层信号引擎 | Task 10, 11, 12, 13 |
| 策略参数 | Task 16 |
| 快照历史 | Task 17 |
| 相关性/风险分析 | Task 9, 15 |
| 免责声明 | Task 14 |
| SQLite 单用户 | Task 2 |
| 错误处理（空持仓、sync 失败） | Task 3, 6, 8 |

无遗漏项。

## 执行顺序建议

严格按 Task 1 → 19 顺序；M1 完成后应可演示「导入 → 概览」；M2 后演示「sync → 再平衡信号」；M3 完整信号；M4 polish。
