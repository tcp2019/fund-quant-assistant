import json

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.models import FundMetadata, FundMetricsCache, Holding, PortfolioSnapshot, SignalRecord
from app.db.session import engine
from app.main import app
from app.services.signals.engine import aggregate_signals, run_signal_engine
from app.services.fund_purchase_limits import apply_purchase_limits_to_signal, parse_purchase_record

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


def test_aggregate_signals_weak_rebalance_add_classified_as_add():
    rebalance = [
        {
            "category": "stock",
            "signal_type": "add",
            "deviation_pct": 9.1,
            "suggested_amount": 52806.0,
            "detail": "股票型低配 9.1%，建议增配 ¥52806",
        }
    ]
    fund_categories = {f"00{i:04d}": "stock" for i in range(3)}
    market_value_by_code = {
        "000000": 500.0,
        "000001": 800.0,
        "000002": 900.0,
    }

    results = aggregate_signals(
        rebalance,
        [],
        [],
        fund_categories,
        market_value_by_code=market_value_by_code,
        total_value=10000.0,
        category_targets={"stock": 0.4},
        intra_category_mode="equal",
    )
    fund_results = [item for item in results if item["fund_code"]]

    assert len(fund_results) == 3
    amounts = [item["suggested_amount"] for item in fund_results]
    assert abs(sum(amounts) - 52806.0) < 0.1
    assert len(set(amounts)) > 1
    for item in fund_results:
        assert item["signal_type"] == "add"
        assert item["reasons"][0]["rule"] == "category_underweight"
        assert item["suggested_amount"] > 0


def test_aggregate_signals_allocates_by_intra_category_gap_not_equal_split():
    rebalance = [
        {
            "category": "stock",
            "signal_type": "add",
            "deviation_pct": 9.1,
            "suggested_amount": 3000.0,
            "detail": "股票型低配 9.1%，建议增配 ¥3000",
        }
    ]
    fund_categories = {"A": "stock", "B": "stock", "C": "stock"}
    market_value_by_code = {"A": 500.0, "B": 2500.0, "C": 2500.0}

    results = aggregate_signals(
        rebalance,
        [],
        [],
        fund_categories,
        market_value_by_code=market_value_by_code,
        total_value=10000.0,
        category_targets={"stock": 0.4},
        intra_category_mode="equal",
    )
    by_code = {item["fund_code"]: item for item in results if item["fund_code"]}
    assert by_code["A"]["suggested_amount"] > by_code["B"]["suggested_amount"]


def test_aggregate_signals_performance_blocked_gets_zero_amount():
    rebalance = [
        {
            "category": "stock",
            "signal_type": "add",
            "deviation_pct": 10.0,
            "suggested_amount": 1000.0,
            "detail": "股票型低配",
        }
    ]
    performance = [
        {
            "fund_code": "A",
            "signal_type": "reduce",
            "reasons": [{"layer": "performance", "rule": "excess_return_1y", "detail": "差"}],
            "detail": "差",
        }
    ]
    results = aggregate_signals(
        rebalance,
        [],
        performance,
        {"A": "stock", "B": "stock"},
        market_value_by_code={"A": 100.0, "B": 1000.0},
        total_value=10000.0,
        category_targets={"stock": 0.5},
        intra_category_mode="equal",
    )
    by_code = {item["fund_code"]: item for item in results if item["fund_code"]}
    assert by_code["A"]["suggested_amount"] == 0.0
    assert by_code["B"]["suggested_amount"] > 0


def test_weak_rebalance_add_downgrades_when_purchase_limit_blocks():
    signal = {
        "fund_code": "012922",
        "signal_type": "add",
        "score": 18.3,
        "strength": 2,
        "suggested_amount": 1703.0,
        "reasons": [
            {
                "layer": "rebalance",
                "rule": "category_underweight",
                "detail": "股票型低配 9.1%，建议增配 ¥52806",
            }
        ],
    }
    purchase_info = parse_purchase_record(
        {
            "purchase_status": "限大额",
            "purchase_min_amount": 10.0,
            "daily_purchase_limit": 20.0,
        }
    )

    updated = apply_purchase_limits_to_signal(signal, purchase_info)

    assert updated["signal_type"] == "watch"
    assert updated["suggested_amount"] == 20.0


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

    results = aggregate_signals(
        rebalance,
        concentration,
        performance,
        fund_categories,
        market_value_by_code={"110011": 5000.0, "000001": 1000.0},
        total_value=6000.0,
        category_targets={"stock": 0.4, "bond": 0.3, "money": 0.15, "qdii": 0.1, "other": 0.05},
        intra_category_mode="equal",
    )
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
    monkeypatch.setattr("app.services.data_sync.fetch_purchase_limits_from_akshare", lambda: {})

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
