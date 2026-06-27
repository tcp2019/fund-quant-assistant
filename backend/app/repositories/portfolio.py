import json

from sqlmodel import Session, select

from app.db.models import FundMetadata, FundNavHistory, Holding, PortfolioSnapshot
from app.schemas.portfolio import (
    CategoryAllocationOut,
    HoldingIn,
    HoldingOut,
    HoldingThemeOut,
    OverviewOut,
    SnapshotCreate,
    SnapshotSummaryOut,
    ThemeAllocationOut,
)
from app.services.fund_classifier import classify_fund
from app.services.fund_themes import detect_themes, primary_theme, theme_label
from app.services.peer_metrics import parse_user_themes
from app.services.signals.rebalance import CATEGORY_LABELS

CATEGORY_DISPLAY_LABELS = {**CATEGORY_LABELS, "gold": "黄金"}


def get_latest_snapshot(session: Session) -> PortfolioSnapshot | None:
    return session.exec(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.created_at.desc())
    ).first()


def _merge_holding(existing: HoldingIn, incoming: HoldingIn) -> HoldingIn:
    total_shares = existing.shares + incoming.shares
    total_market_value = existing.market_value + incoming.market_value
    total_profit = existing.profit + incoming.profit

    if total_shares > 0:
        cost_price = (
            existing.cost_price * existing.shares + incoming.cost_price * incoming.shares
        ) / total_shares
    elif total_market_value > 0:
        cost_price = (
            existing.cost_price * existing.market_value + incoming.cost_price * incoming.market_value
        ) / total_market_value
    else:
        cost_price = existing.cost_price or incoming.cost_price

    implied_cost = total_market_value - total_profit
    profit_rate = total_profit / implied_cost if implied_cost > 0 else 0.0

    return HoldingIn(
        fund_code=incoming.fund_code,
        fund_name=existing.fund_name,
        shares=total_shares,
        cost_price=cost_price,
        market_value=total_market_value,
        profit=total_profit,
        profit_rate=profit_rate,
        platform=f"{existing.platform},{incoming.platform}",
        hold_days=existing.hold_days or incoming.hold_days,
    )


def create_snapshot(session: Session, data: SnapshotCreate) -> PortfolioSnapshot:
    snap = PortfolioSnapshot(source=data.source, note=data.note)
    session.add(snap)
    session.commit()
    session.refresh(snap)

    merged: dict[tuple[str, str], HoldingIn] = {}
    for h in data.holdings:
        key = (h.fund_code, h.fund_name)
        if key in merged:
            merged[key] = _merge_holding(merged[key], h)
        else:
            merged[key] = h

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


def _holding_total_cost(holding: Holding) -> float:
    if holding.shares > 0:
        return holding.shares * holding.cost_price
    if holding.cost_price > 0:
        return holding.cost_price
    return max(holding.market_value - holding.profit, 0.0)


def _classify_holding(session: Session, holding: Holding) -> str:
    meta = session.get(FundMetadata, holding.fund_code)
    fund_type = meta.fund_type if meta else ""
    return classify_fund(holding.fund_name, fund_type)


def _holding_themes_out(session: Session, holding: Holding) -> list[HoldingThemeOut]:
    return [
        HoldingThemeOut(theme=theme_id, label=theme_label(theme_id))
        for theme_id in _holding_themes(session, holding)
    ]


def _holding_to_out(session: Session, holding: Holding, weight_pct: float) -> HoldingOut:
    return HoldingOut(
        fund_code=holding.fund_code,
        fund_name=holding.fund_name,
        shares=holding.shares,
        cost_price=holding.cost_price,
        market_value=holding.market_value,
        profit=holding.profit,
        profit_rate=holding.profit_rate,
        platform=holding.platform,
        hold_days=holding.hold_days,
        weight_pct=round(weight_pct, 2),
        themes=_holding_themes_out(session, holding),
    )


def _holding_themes(session: Session, holding: Holding) -> list[str]:
    meta = session.get(FundMetadata, holding.fund_code)
    if meta and meta.themes_json:
        try:
            themes = json.loads(meta.themes_json)
            if isinstance(themes, list) and themes:
                return [item for item in themes if isinstance(item, str)]
        except json.JSONDecodeError:
            pass
    user_themes = parse_user_themes(meta.user_themes_json) if meta else []
    fund_type = meta.fund_type if meta else ""
    return detect_themes(holding.fund_name, fund_type, user_themes)


def _portfolio_as_of_date(session: Session, fund_codes: list[str]) -> str | None:
    dates: list[str] = []
    for code in fund_codes:
        row = session.exec(
            select(FundNavHistory)
            .where(FundNavHistory.code == code)
            .order_by(FundNavHistory.date.desc())
        ).first()
        if row:
            dates.append(row.date)
    return max(dates) if dates else None


def _build_theme_allocation(
    session: Session, holdings: list[Holding], total_value: float
) -> list[ThemeAllocationOut]:
    if not holdings or total_value <= 0:
        return []

    theme_values: dict[str, float] = {}
    for holding in holdings:
        meta = session.get(FundMetadata, holding.fund_code)
        fund_type = meta.fund_type if meta else ""
        theme = primary_theme(holding.fund_name, fund_type)
        if theme is None:
            themes = _holding_themes(session, holding)
            theme = themes[0] if themes else None
        if theme is None:
            continue
        theme_values[theme] = theme_values.get(theme, 0.0) + holding.market_value

    allocation = [
        ThemeAllocationOut(
            theme=theme,
            label=theme_label(theme),
            weight_pct=round(value / total_value * 100, 2),
            market_value=round(value, 2),
        )
        for theme, value in theme_values.items()
    ]
    return sorted(allocation, key=lambda item: item.weight_pct, reverse=True)


def _build_category_allocation(
    session: Session, holdings: list[Holding], total_value: float
) -> list[CategoryAllocationOut]:
    if not holdings or total_value <= 0:
        return []

    category_values: dict[str, float] = {}
    for holding in holdings:
        category = _classify_holding(session, holding)
        category_values[category] = category_values.get(category, 0.0) + holding.market_value

    allocation = [
        CategoryAllocationOut(
            category=category,
            label=CATEGORY_DISPLAY_LABELS.get(category, category),
            weight_pct=round(value / total_value * 100, 2),
            market_value=round(value, 2),
        )
        for category, value in category_values.items()
    ]
    return sorted(allocation, key=lambda item: item.weight_pct, reverse=True)


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
    total_cost = sum(_holding_total_cost(h) for h in holdings)
    total_profit = sum(h.profit for h in holdings)
    total_profit_rate = (total_profit / total_cost) if total_cost else 0.0

    out_holdings: list[HoldingOut] = []
    for h in holdings:
        weight = (h.market_value / total_value * 100) if total_value else 0.0
        out_holdings.append(_holding_to_out(session, h, weight))

    sorted_by_weight = sorted(out_holdings, key=lambda item: item.weight_pct, reverse=True)
    top_holdings = sorted_by_weight[:5]
    concentration_top5_pct = round(sum(item.weight_pct for item in top_holdings), 2)

    fund_codes = [h.fund_code for h in holdings]
    return OverviewOut(
        snapshot_id=snap.id,
        total_value=round(total_value, 2),
        total_cost=round(total_cost, 2),
        total_profit=round(total_profit, 2),
        total_profit_rate=round(total_profit_rate, 4),
        holdings=out_holdings,
        category_allocation=_build_category_allocation(session, holdings, total_value),
        theme_allocation=_build_theme_allocation(session, holdings, total_value),
        top_holdings=top_holdings,
        concentration_top5_pct=concentration_top5_pct,
        data_as_of_date=_portfolio_as_of_date(session, fund_codes),
    )
