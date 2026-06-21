import json

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.models import FundMetadata, FundMetricsCache, Holding, PortfolioSnapshot, SignalRecord
from app.db.session import engine
from app.main import app
from app.services.signals.engine import aggregate_signals, run_signal_engine

client = TestClient(app)


def _seed_snapshot(session: Session) -> PortfolioSnapshot:
    snap = PortfolioSnapshot(source="manual", note="signal engine test")
    session.add(snap)
    session.commit()
    session.refresh(snap)

    session.add(
        Holding(
            snapshot_id=snap.id,
            fund_code="110011",
            fund_name="易方达优质精选混合",
            shares=1000,
            cost_price=1.5,
            market_value=5000,
            profit=500,
            hold_days=30,
        )
    )
    session.add(
        Holding(
            snapshot_id=snap.id,
            fund_code="000001",
            fund_name="华夏债券A",
            shares=800,
            cost_price=1.0,
            market_value=1000,
            profit=50,
            hold_days=60,
        )
    )
    session.add(
        FundMetadata(
            code="110011",
            name="易方达优质精选混合",
            fund_type="混合型",
            category="stock",
        )
    )
    session.add(
        FundMetadata(
            code="000001",
            name="华夏债券A",
            fund_type="债券型",
            category="bond",
        )
    )
    session.add(
        FundMetricsCache(
            code="110011",
            as_of_date="2025-06-01",
            sharpe_1y=0.5,
            max_drawdown_1y=-0.25,
            excess_return_1y=-0.08,
        )
    )
    session.commit()
    return snap


def test_aggregate_signals_merges_layers():
    rebalance = [
        {
            "category": "bond",
            "signal_type": "add",
            "deviation_pct": 10.0,
            "suggested_amount": 800.0,
            "detail": "债券型低配 10.0%，建议增配 ¥800",
        }
    ]
    concentration = [
        {
            "fund_code": "110011",
            "signal_type": "reduce",
            "weight_pct": 83.3,
            "detail": "单只占比 83.3% 超过 25%，建议减仓分散风险",
        }
    ]
    performance = [
        {
            "fund_code": "110011",
            "signal_type": "reduce",
            "reasons": [
                {
                    "layer": "performance",
                    "rule": "excess_return_1y",
                    "detail": "近1年超额收益 -8.0%，低于基准 5%",
                }
            ],
            "detail": "近1年超额收益 -8.0%，低于基准 5%",
        },
        {
            "fund_code": "000001",
            "signal_type": "hold",
            "reasons": [],
            "detail": "业绩质量正常",
        },
    ]
    fund_categories = {"110011": "stock", "000001": "bond"}

    results = aggregate_signals(rebalance, concentration, performance, fund_categories)
    by_code = {item["fund_code"]: item for item in results if item["fund_code"]}

    assert by_code["110011"]["signal_type"] == "reduce"
    assert by_code["110011"]["score"] < 0
    assert 1 <= by_code["110011"]["strength"] <= 5

    category_adds = [item for item in results if not item["fund_code"]]
    assert len(category_adds) == 1
    assert category_adds[0]["signal_type"] == "add"
    assert category_adds[0]["suggested_amount"] == 800.0


def test_run_signal_engine_writes_records():
    with Session(engine) as session:
        snap = _seed_snapshot(session)
        records = run_signal_engine(session)

        assert len(records) >= 3
        stored = session.exec(
            select(SignalRecord).where(SignalRecord.snapshot_id == snap.id)
        ).all()
        assert len(stored) == len(records)

        stock_signal = next(r for r in stored if r.fund_code == "110011")
        assert stock_signal.score < 0
        assert stock_signal.signal_type in ("reduce", "watch")

        category_add = next(r for r in stored if r.fund_code == "")
        assert category_add.signal_type == "add"
        reasons = json.loads(category_add.reasons_json)
        assert reasons[0]["layer"] == "rebalance"


def test_api_signals_sorted_by_score(monkeypatch):
    def fake_fetch(code: str):
        return [{"date": "2025-06-01", "nav": 1.5, "acc_nav": 1.5}]

    def fake_metadata(code: str):
        return {
            "name": "测试基金",
            "fund_type": "混合型",
            "manager": "测试",
            "benchmark_code": "",
        }

    monkeypatch.setattr("app.services.data_sync.fetch_nav_from_akshare", fake_fetch)
    monkeypatch.setattr("app.services.data_sync.fetch_metadata_from_akshare", fake_metadata)

    payload = {
        "holdings": [
            {
                "fund_code": "110011",
                "fund_name": "易方达优质精选混合",
                "shares": 1000,
                "cost_price": 1.5,
                "market_value": 5000,
                "profit": 500,
                "platform": "alipay",
                "hold_days": 30,
            },
            {
                "fund_code": "000001",
                "fund_name": "华夏债券A",
                "shares": 800,
                "cost_price": 1.0,
                "market_value": 1000,
                "profit": 50,
                "platform": "alipay",
                "hold_days": 60,
            },
        ],
        "source": "manual",
    }
    client.post("/api/portfolio/snapshots", json=payload)

    with Session(engine) as session:
        session.add(
            FundMetricsCache(
                code="110011",
                as_of_date="2025-06-01",
                sharpe_1y=0.5,
                max_drawdown_1y=-0.25,
                excess_return_1y=-0.08,
            )
        )
        session.commit()

    sync_resp = client.post("/api/data/sync")
    assert sync_resp.status_code == 200
    assert sync_resp.json()["signals_count"] >= 1

    resp = client.get("/api/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["snapshot_id"] is not None
    scores = [signal["score"] for signal in data["signals"]]
    assert scores == sorted(scores, reverse=True)
