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
