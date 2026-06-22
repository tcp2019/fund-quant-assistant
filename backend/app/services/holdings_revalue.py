from sqlmodel import Session, select

from app.db.models import FundNavHistory, Holding, PortfolioSnapshot
from app.repositories.portfolio import get_latest_snapshot


def _latest_nav(session: Session, code: str) -> tuple[str, float] | None:
    row = session.exec(
        select(FundNavHistory)
        .where(FundNavHistory.code == code)
        .order_by(FundNavHistory.date.desc())
    ).first()
    if row is None:
        return None
    return row.date, row.nav


def revalue_holdings(session: Session, snapshot_id: int | None = None) -> dict[str, object]:
    snap_id = snapshot_id
    if snap_id is None:
        snap = get_latest_snapshot(session)
        if snap is None:
            return {"updated": 0, "as_of_date": None}
        snap_id = snap.id

    holdings = session.exec(select(Holding).where(Holding.snapshot_id == snap_id)).all()
    updated = 0
    as_of_dates: list[str] = []

    for holding in holdings:
        if holding.shares <= 0:
            continue
        latest = _latest_nav(session, holding.fund_code)
        if latest is None:
            continue
        as_of_date, nav = latest
        as_of_dates.append(as_of_date)
        cost_basis = holding.shares * holding.cost_price
        new_market_value = round(holding.shares * nav, 2)
        new_profit = round(new_market_value - cost_basis, 2) if holding.cost_price > 0 else holding.profit
        new_profit_rate = round(new_profit / cost_basis, 4) if cost_basis > 0 else holding.profit_rate

        holding.market_value = new_market_value
        holding.profit = new_profit
        holding.profit_rate = new_profit_rate
        updated += 1

    session.commit()
    portfolio_as_of = max(as_of_dates) if as_of_dates else None
    return {"updated": updated, "as_of_date": portfolio_as_of}
