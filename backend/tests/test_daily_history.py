from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.models import FundNavHistory, Holding, PortfolioSnapshot
from app.db.session import engine
from app.main import app
from app.repositories.portfolio import build_daily_history

client = TestClient(app)


def test_build_daily_history_empty_portfolio():
    with Session(engine) as session:
        result = build_daily_history(session, days=30)
        assert result.days == 30
        assert result.points == []


def test_build_daily_history_daily_profit_per_fund_prev_day():
    with Session(engine) as session:
        snap = PortfolioSnapshot(source="test")
        session.add(snap)
        session.commit()
        session.refresh(snap)

        session.add(
            Holding(
                snapshot_id=snap.id,
                fund_code="110011",
                fund_name="基金A",
                shares=1000.0,
                cost_price=1.0,
                market_value=1100.0,
                profit=100.0,
                profit_rate=0.1,
            )
        )
        session.add(
            Holding(
                snapshot_id=snap.id,
                fund_code="110022",
                fund_name="基金B",
                shares=500.0,
                cost_price=2.0,
                market_value=1050.0,
                profit=50.0,
                profit_rate=0.05,
            )
        )
        for code, navs in [
            ("110011", [("2026-06-24", 1.0), ("2026-06-25", 1.1), ("2026-06-26", 1.15)]),
            ("110022", [("2026-06-24", 2.0), ("2026-06-25", 2.1), ("2026-06-26", 2.0)]),
        ]:
            for date, nav in navs:
                session.add(FundNavHistory(code=code, date=date, nav=nav, acc_nav=nav))
        session.commit()

        result = build_daily_history(session, days=30)
        by_date = {point.date: point for point in result.points}

        assert len(result.points) == 2
        assert by_date["2026-06-25"].daily_profit == 150.0
        assert by_date["2026-06-25"].complete is True
        assert by_date["2026-06-26"].daily_profit == 0.0
        assert by_date["2026-06-26"].total_value == 1000 * 1.15 + 500 * 2.0


def test_daily_history_api_clamps_days():
    resp = client.get("/api/portfolio/daily-history?days=3")
    assert resp.status_code == 200
    assert resp.json()["days"] == 7

    resp = client.get("/api/portfolio/daily-history?days=45")
    assert resp.json()["days"] == 45
