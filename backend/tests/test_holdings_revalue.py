from sqlmodel import Session, select

from app.db.models import FundNavHistory, Holding
from app.db.models import PortfolioSnapshot
from app.db.session import engine
from app.services.holdings_revalue import revalue_holdings


def test_revalue_holdings_updates_market_value_from_nav():
    with Session(engine) as session:
        snap = PortfolioSnapshot(source="test")
        session.add(snap)
        session.commit()
        session.refresh(snap)

        session.add(
            Holding(
                snapshot_id=snap.id,
                fund_code="110011",
                fund_name="易方达优质精选",
                shares=1000.0,
                cost_price=1.0,
                market_value=900.0,
                profit=-100.0,
                profit_rate=-0.1,
            )
        )
        session.add(
            FundNavHistory(code="110011", date="2026-06-20", nav=1.05, acc_nav=1.05)
        )
        session.commit()

        result = revalue_holdings(session, snap.id)
        assert result["updated"] == 1
        assert result["as_of_date"] == "2026-06-20"

        holding = session.exec(
            select(Holding).where(Holding.snapshot_id == snap.id)
        ).one()
        assert holding.market_value == 1050.0
        assert holding.profit == 50.0


def test_revalue_skips_zero_shares():
    with Session(engine) as session:
        snap = PortfolioSnapshot(source="test")
        session.add(snap)
        session.commit()
        session.refresh(snap)

        session.add(
            Holding(
                snapshot_id=snap.id,
                fund_code="110011",
                fund_name="易方达优质精选",
                shares=0.0,
                cost_price=0.0,
                market_value=5000.0,
            )
        )
        session.commit()

        result = revalue_holdings(session, snap.id)
        assert result["updated"] == 0
