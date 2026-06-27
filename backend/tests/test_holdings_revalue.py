from sqlmodel import Session, select

import pytest

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
        assert overview.daily_total_profit is None
        assert overview.nav_anomalies == []
        assert overview.holdings[0].current_value == 1000.0
        assert overview.holdings[0].nav_date is None
        assert overview.holdings[0].daily_profit is None


def test_build_overview_includes_daily_profit():
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
        assert overview.daily_total_profit == 50.0  # 1000 × (1.15 - 1.10)
        assert overview.nav_anomalies == []

        holding = overview.holdings[0]
        assert holding.daily_profit == 50.0
        assert holding.prev_nav_date == "2026-06-25"
        assert holding.nav_change_pct == pytest.approx(0.0455, rel=1e-3)


def test_build_overview_daily_profit_null_with_single_nav_row():
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
                market_value=1150.0,
                profit=150.0,
            )
        )
        session.add(
            FundNavHistory(code="110011", date="2026-06-26", nav=1.15, acc_nav=1.15)
        )
        session.commit()

        overview = build_overview(session)
        assert overview.daily_total_profit is None
        assert overview.holdings[0].daily_profit is None


def test_build_overview_detects_nav_anomaly():
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
            FundNavHistory(code="110011", date="2026-06-25", nav=1.00, acc_nav=1.00)
        )
        session.add(
            FundNavHistory(code="110011", date="2026-06-26", nav=1.20, acc_nav=1.20)
        )
        session.commit()

        overview = build_overview(session)
        assert len(overview.nav_anomalies) == 1
        anomaly = overview.nav_anomalies[0]
        assert anomaly.fund_code == "110011"
        assert anomaly.change_pct == 20.0
        assert anomaly.prev_nav_date == "2026-06-25"
        assert anomaly.nav_date == "2026-06-26"


def test_build_overview_daily_total_null_when_portfolio_incomplete():
    """组合今日盈亏仅在全部有份额持仓均可算时才返回，避免部分合计误导。"""
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
                market_value=1150.0,
                profit=150.0,
            )
        )
        session.add(
            Holding(
                snapshot_id=snap.id,
                fund_code="110022",
                fund_name="易方达消费",
                shares=500.0,
                cost_price=2.0,
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
        session.add(
            FundNavHistory(code="110022", date="2026-06-26", nav=2.00, acc_nav=2.00)
        )
        session.commit()

        overview = build_overview(session)
        assert overview.daily_total_profit is None
        by_code = {h.fund_code: h for h in overview.holdings}
        assert by_code["110011"].daily_profit == 50.0
        assert by_code["110022"].daily_profit is None
