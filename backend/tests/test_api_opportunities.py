from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.models import FundMetadata, Holding, PortfolioSnapshot
from app.db.session import engine
from app.main import app
from app.services.opportunities import build_opportunities
from app.services.signals.engine import run_signal_engine

client = TestClient(app)


def test_opportunities_empty_snapshot():
    resp = client.get("/api/opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["snapshot_id"] is None
    assert data["structural_actions"] == []
    assert data["sell_actions"] == []


def test_opportunities_includes_structural_actions():
    with Session(engine) as session:
        snap = PortfolioSnapshot(source="manual", note="structural test")
        session.add(snap)
        session.commit()
        session.refresh(snap)

        for index in range(12):
            code = f"ST{index:04d}"
            session.add(
                Holding(
                    snapshot_id=snap.id,
                    fund_code=code,
                    fund_name=f"测试股票基金{index}",
                    shares=100,
                    cost_price=1.0,
                    market_value=5000.0,
                    profit=0,
                    hold_days=30,
                )
            )
            session.add(
                FundMetadata(
                    code=code,
                    name=f"测试股票基金{index}",
                    fund_type="股票型",
                    category="stock",
                )
            )
        session.commit()
        run_signal_engine(session)

        result = build_opportunities(session)
        assert any(action.action == "consolidate" for action in result.structural_actions)
        assert result.buy_actions == []

    resp = client.get("/api/opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert "structural_actions" in data
    assert any(item["action"] == "consolidate" for item in data["structural_actions"])

