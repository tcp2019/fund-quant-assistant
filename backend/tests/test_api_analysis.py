from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.models import FundNavHistory, Holding, PortfolioSnapshot
from app.db.session import engine
from app.main import app

client = TestClient(app)


def _seed_snapshot_with_nav():
    with Session(engine) as session:
        snap = PortfolioSnapshot(source="manual")
        session.add(snap)
        session.commit()
        session.refresh(snap)

        session.add(
            Holding(
                snapshot_id=snap.id,
                fund_code="110011",
                fund_name="易方达优质精选",
                shares=1000,
                cost_price=1.5,
                market_value=6000,
            )
        )
        session.add(
            Holding(
                snapshot_id=snap.id,
                fund_code="000001",
                fund_name="华夏成长",
                shares=500,
                cost_price=2.0,
                market_value=4000,
            )
        )
        session.commit()

        for day in range(1, 16):
            date = f"2025-06-{day:02d}"
            session.add(
                FundNavHistory(code="110011", date=date, nav=1.0 + day * 0.01, acc_nav=1.0 + day * 0.01)
            )
            session.add(
                FundNavHistory(
                    code="000001",
                    date=date,
                    nav=2.0 + day * 0.008,
                    acc_nav=2.0 + day * 0.008,
                )
            )
        session.commit()
        return snap.id


def test_correlation_empty():
    resp = client.get("/api/analysis/correlation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["snapshot_id"] is None
    assert data["labels"] == []
    assert data["matrix"] == []


def test_correlation_with_holdings_and_nav():
    snapshot_id = _seed_snapshot_with_nav()
    resp = client.get("/api/analysis/correlation")
    assert resp.status_code == 200
    data = resp.json()
    assert data["snapshot_id"] == snapshot_id
    assert data["labels"] == ["110011", "000001"]
    assert len(data["matrix"]) == 2
    assert len(data["matrix"][0]) == 2
    assert data["matrix"][0][0] == 1.0
    assert data["matrix"][1][1] == 1.0
    assert data["matrix"][0][1] == data["matrix"][1][0]
    assert data["matrix"][0][1] > 0.9


def test_risk_empty():
    resp = client.get("/api/analysis/risk")
    assert resp.status_code == 200
    data = resp.json()
    assert data["snapshot_id"] is None
    assert data["volatility"] is None
    assert data["sharpe"] is None
    assert data["max_dd"] is None


def test_risk_with_holdings_and_nav():
    snapshot_id = _seed_snapshot_with_nav()
    resp = client.get("/api/analysis/risk")
    assert resp.status_code == 200
    data = resp.json()
    assert data["snapshot_id"] == snapshot_id
    assert data["volatility"] is not None
    assert data["sharpe"] is not None
    assert data["max_dd"] is not None
    assert data["volatility"] > 0
    assert data["period_days"] >= 2
