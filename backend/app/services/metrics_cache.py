from datetime import datetime

from sqlmodel import Session, select

from app.db.models import FundMetricsCache, FundNavHistory
from app.services.metrics import daily_returns_from_navs, max_drawdown, sharpe_ratio

LOOKBACK_DAYS = 252


def compute_and_cache_metrics(session: Session, code: str) -> FundMetricsCache | None:
    rows = session.exec(
        select(FundNavHistory)
        .where(FundNavHistory.code == code)
        .order_by(FundNavHistory.date.desc())
        .limit(LOOKBACK_DAYS + 1)
    ).all()
    if len(rows) < 2:
        return None

    rows = list(reversed(rows))
    navs = [row.nav for row in rows]
    returns = daily_returns_from_navs(navs)
    if len(returns) < 2:
        return None

    as_of_date = rows[-1].date
    sharpe = sharpe_ratio(returns[-LOOKBACK_DAYS:])
    max_dd = max_drawdown(returns[-LOOKBACK_DAYS:])
    return_1y = (navs[-1] / navs[0]) - 1 if navs[0] else None

    existing = session.exec(
        select(FundMetricsCache)
        .where(FundMetricsCache.code == code)
        .order_by(FundMetricsCache.as_of_date.desc())
    ).first()

    if existing:
        existing.as_of_date = as_of_date
        existing.sharpe_1y = round(sharpe, 4)
        existing.max_drawdown_1y = round(max_dd, 4)
        existing.return_1y = round(return_1y, 4) if return_1y is not None else None
        existing.computed_from = "nav_history"
        record = existing
    else:
        record = FundMetricsCache(
            code=code,
            as_of_date=as_of_date,
            sharpe_1y=round(sharpe, 4),
            max_drawdown_1y=round(max_dd, 4),
            return_1y=round(return_1y, 4) if return_1y is not None else None,
            peer_return_percentile_3m=None,
            computed_from="nav_history",
        )
        session.add(record)

    session.commit()
    session.refresh(record)
    return record
