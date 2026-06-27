from sqlmodel import Session, select

from app.db.models import FundNavHistory, Holding
from app.db.models import PortfolioSnapshot
from app.db.session import engine
from app.repositories.portfolio import build_overview
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


def test_build_overview_includes_current_values():
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
                market_value=1000.0,
                profit=0.0,
            )
        )
        session.add(
            FundNavHistory(code="110011", date="2026-06-25", nav=1.10, acc_nav=1.10)
        )
        session.add(
            FundNavHistory(code="110011", date="2026-06-26", nav=1.15, acc_nav=1.15)
        )
        session.commit()

        overview = build_overview(session)
        assert overview.snapshot_id == snap.id
        # snapshot values unchanged
        assert overview.total_value == 1000.0
        # real-time values from latest NAV
        assert overview.current_total_value == 1150.0  # 1000 shares × 1.15
        assert overview.current_total_profit == 150.0
        assert overview.current_total_profit_rate == 0.15
        assert overview.nav_date == "2026-06-26"

        holding = overview.holdings[0]
        assert holding.current_value == 1150.0
        assert holding.current_profit == 150.0
        assert holding.nav_date == "2026-06-26"


def test_build_overview_falls_back_when_no_nav_data():
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
                market_value=1000.0,
                profit=0.0,
            )
        )
        session.commit()

        overview = build_overview(session)
        # falls back to snapshot values when no NAV data
        assert overview.current_total_value == 1000.0
        assert overview.nav_date is None
        assert overview.holdings[0].current_value == 1000.0
        assert overview.holdings[0].nav_date is None
