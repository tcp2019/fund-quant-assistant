from sqlmodel import Session
from app.db.models import PortfolioSnapshot
from app.services.backtest_engine import run_history_backtest


def test_backtest_needs_two_snapshots(session: Session):
    result = run_history_backtest(session)
    assert result["snapshots_tested"] == 0
    assert "至少 2 个" in result["detail"]


def test_backtest_with_data(session: Session):
    for _ in range(3):
        snap = PortfolioSnapshot()
        session.add(snap)
    session.commit()
    result = run_history_backtest(session)
    assert result["snapshots_tested"] == 3
