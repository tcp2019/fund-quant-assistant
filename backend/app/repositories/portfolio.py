from sqlmodel import Session, select

from app.db.models import Holding, PortfolioSnapshot
from app.schemas.portfolio import HoldingIn, OverviewOut, SnapshotCreate, SnapshotSummaryOut


def get_latest_snapshot(session: Session) -> PortfolioSnapshot | None:
    return session.exec(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.created_at.desc())
    ).first()


def create_snapshot(session: Session, data: SnapshotCreate) -> PortfolioSnapshot:
    snap = PortfolioSnapshot(source=data.source, note=data.note)
    session.add(snap)
    session.commit()
    session.refresh(snap)

    merged: dict[str, HoldingIn] = {}
    for h in data.holdings:
        if h.fund_code in merged:
            existing = merged[h.fund_code]
            merged[h.fund_code] = HoldingIn(
                fund_code=h.fund_code,
                fund_name=h.fund_name,
                shares=existing.shares + h.shares,
                cost_price=(existing.cost_price * existing.shares + h.cost_price * h.shares)
                / (existing.shares + h.shares),
                market_value=existing.market_value + h.market_value,
                profit=existing.profit + h.profit,
                profit_rate=0.0,
                platform=f"{existing.platform},{h.platform}",
            )
        else:
            merged[h.fund_code] = h

    for h in merged.values():
        session.add(
            Holding(
                snapshot_id=snap.id,
                fund_code=h.fund_code,
                fund_name=h.fund_name,
                shares=h.shares,
                cost_price=h.cost_price,
                market_value=h.market_value,
                profit=h.profit,
                profit_rate=h.profit_rate,
                platform=h.platform,
                hold_days=h.hold_days,
            )
        )
    session.commit()
    return snap


def list_snapshots(session: Session) -> list[SnapshotSummaryOut]:
    snaps = session.exec(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.created_at.desc())
    ).all()
    summaries: list[SnapshotSummaryOut] = []
    for snap in snaps:
        holdings = session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
        total_value = round(sum(h.market_value for h in holdings), 2)
        summaries.append(
            SnapshotSummaryOut(
                id=snap.id,
                created_at=snap.created_at,
                source=snap.source,
                total_value=total_value,
            )
        )
    return summaries


def build_overview(session: Session) -> OverviewOut:
    snap = get_latest_snapshot(session)
    if not snap:
        return OverviewOut(
            snapshot_id=None,
            total_value=0,
            total_cost=0,
            total_profit=0,
            total_profit_rate=0,
            holdings=[],
        )

    holdings = session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
    total_value = sum(h.market_value for h in holdings)
    total_cost = sum(h.shares * h.cost_price for h in holdings)
    total_profit = sum(h.profit for h in holdings)
    total_profit_rate = (total_profit / total_cost) if total_cost else 0.0

    out_holdings = []
    for h in holdings:
        weight = (h.market_value / total_value * 100) if total_value else 0.0
        out_holdings.append(
            {
                "fund_code": h.fund_code,
                "fund_name": h.fund_name,
                "shares": h.shares,
                "cost_price": h.cost_price,
                "market_value": h.market_value,
                "profit": h.profit,
                "profit_rate": h.profit_rate,
                "platform": h.platform,
                "hold_days": h.hold_days,
                "weight_pct": round(weight, 2),
            }
        )

    return OverviewOut(
        snapshot_id=snap.id,
        total_value=round(total_value, 2),
        total_cost=round(total_cost, 2),
        total_profit=round(total_profit, 2),
        total_profit_rate=round(total_profit_rate, 4),
        holdings=out_holdings,
    )
