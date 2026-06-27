from sqlmodel import Session

from app.db.models import FundNavHistory, Holding, PortfolioSnapshot
from app.services.analysis import _aligned_nav_series


def test_aligned_nav_series_uses_acc_nav_by_default(session: Session):
    snap = PortfolioSnapshot()
    session.add(snap)
    session.commit()

    h = Holding(snapshot_id=snap.id, fund_code="110011", fund_name="测试",
                shares=100, cost_price=1.0, market_value=100)
    session.add(h)
    session.commit()

    session.add(FundNavHistory(code="110011", date="2026-01-01", nav=1.0, acc_nav=2.0))
    session.add(FundNavHistory(code="110011", date="2026-01-02", nav=0.5, acc_nav=2.1))
    session.commit()

    labels, series = _aligned_nav_series(session, ["110011"], 90)
    assert len(series) == 1
    assert series[0] == [2.0, 2.1]


def test_aligned_nav_series_falls_back_to_nav(session: Session):
    snap = PortfolioSnapshot()
    session.add(snap)
    session.commit()

    h = Holding(snapshot_id=snap.id, fund_code="110011", fund_name="测试",
                shares=100, cost_price=1.0, market_value=100)
    session.add(h)
    session.commit()

    session.add(FundNavHistory(code="110011", date="2026-01-01", nav=1.0, acc_nav=0.0))
    session.add(FundNavHistory(code="110011", date="2026-01-02", nav=1.05, acc_nav=0.0))
    session.commit()

    labels, series = _aligned_nav_series(session, ["110011"], 90)
    assert series[0] == [1.0, 1.05]
