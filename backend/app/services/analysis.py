import numpy as np
from sqlmodel import Session, select

from app.db.models import FundNavHistory, Holding
from app.repositories.portfolio import get_latest_snapshot
from app.services.metrics import (
    correlation_matrix,
    daily_returns_from_navs,
    max_drawdown,
    sharpe_ratio,
)

CORRELATION_LOOKBACK_DAYS = 90
RISK_LOOKBACK_DAYS = 252


def _nav_by_date(session: Session, code: str, use_acc_nav: bool = True) -> dict[str, float]:
    rows = session.exec(
        select(FundNavHistory)
        .where(FundNavHistory.code == code)
        .order_by(FundNavHistory.date)
    ).all()
    if use_acc_nav and not any(row.acc_nav == 0 for row in rows):
        return {row.date: row.acc_nav for row in rows}
    return {row.date: row.nav for row in rows}


def _aligned_nav_series(
    session: Session,
    fund_codes: list[str],
    lookback_trading_days: int,
    use_acc_nav: bool = True,
) -> tuple[list[str], list[list[float]]]:
    if not fund_codes:
        return [], []

    nav_maps = {code: _nav_by_date(session, code, use_acc_nav) for code in fund_codes}

    common_dates = None
    for code in fund_codes:
        dates = set(nav_maps[code].keys())
        common_dates = dates if common_dates is None else common_dates & dates

    if not common_dates:
        return fund_codes, []

    sorted_dates = sorted(common_dates)
    if len(sorted_dates) > lookback_trading_days + 1:
        sorted_dates = sorted_dates[-(lookback_trading_days + 1):]

    series_list: list[list[float]] = []
    for code in fund_codes:
        navs = [nav_maps[code][date] for date in sorted_dates]
        series_list.append(navs)

    return fund_codes, series_list


def _returns_from_nav_series(nav_series: list[list[float]]) -> list[np.ndarray]:
    returns_list: list[np.ndarray] = []
    for navs in nav_series:
        rets = daily_returns_from_navs(navs)
        if len(rets) > 0:
            returns_list.append(rets)
        else:
            returns_list.append(np.array([]))
    return returns_list


def compute_correlation(session: Session) -> dict:
    snap = get_latest_snapshot(session)
    if snap is None:
        return {
            "snapshot_id": None,
            "labels": [],
            "matrix": [],
            "period_days": CORRELATION_LOOKBACK_DAYS,
        }

    holdings = session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
    if not holdings:
        return {
            "snapshot_id": snap.id,
            "labels": [],
            "matrix": [],
            "period_days": CORRELATION_LOOKBACK_DAYS,
        }

    fund_codes = [holding.fund_code for holding in holdings]
    labels, nav_series = _aligned_nav_series(session, fund_codes, CORRELATION_LOOKBACK_DAYS)
    if not nav_series or any(len(navs) < 2 for navs in nav_series):
        n = len(labels)
        identity = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        return {
            "snapshot_id": snap.id,
            "labels": labels,
            "matrix": identity,
            "period_days": CORRELATION_LOOKBACK_DAYS,
        }

    returns_list = _returns_from_nav_series(nav_series)
    min_len = min(len(rets) for rets in returns_list)
    if min_len < 2:
        n = len(labels)
        return {
            "snapshot_id": snap.id,
            "labels": labels,
            "matrix": [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)],
            "period_days": CORRELATION_LOOKBACK_DAYS,
        }

    trimmed = [rets[-min_len:] for rets in returns_list]
    corr = correlation_matrix(trimmed)
    matrix = [[round(float(corr[i, j]), 4) for j in range(len(labels))] for i in range(len(labels))]

    return {
        "snapshot_id": snap.id,
        "labels": labels,
        "matrix": matrix,
        "period_days": min_len,
    }


def compute_risk(session: Session) -> dict:
    snap = get_latest_snapshot(session)
    if snap is None:
        return {
            "snapshot_id": None,
            "volatility": None,
            "sharpe": None,
            "max_dd": None,
            "period_days": RISK_LOOKBACK_DAYS,
        }

    holdings = session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
    if not holdings:
        return {
            "snapshot_id": snap.id,
            "volatility": None,
            "sharpe": None,
            "max_dd": None,
            "period_days": RISK_LOOKBACK_DAYS,
        }

    total_value = sum(holding.market_value for holding in holdings)
    if total_value <= 0:
        return {
            "snapshot_id": snap.id,
            "volatility": None,
            "sharpe": None,
            "max_dd": None,
            "period_days": RISK_LOOKBACK_DAYS,
        }

    fund_codes = [holding.fund_code for holding in holdings]
    weights = np.array(
        [holding.market_value / total_value for holding in holdings],
        dtype=float,
    )

    labels, nav_series = _aligned_nav_series(session, fund_codes, RISK_LOOKBACK_DAYS)
    if not nav_series or any(len(navs) < 2 for navs in nav_series):
        return {
            "snapshot_id": snap.id,
            "volatility": None,
            "sharpe": None,
            "max_dd": None,
            "period_days": RISK_LOOKBACK_DAYS,
        }

    returns_list = _returns_from_nav_series(nav_series)
    min_len = min(len(rets) for rets in returns_list)
    if min_len < 2:
        return {
            "snapshot_id": snap.id,
            "volatility": None,
            "sharpe": None,
            "max_dd": None,
            "period_days": RISK_LOOKBACK_DAYS,
        }

    trimmed = [rets[-min_len:] for rets in returns_list]
    stacked = np.column_stack(trimmed)
    portfolio_returns = stacked @ weights

    volatility = float(portfolio_returns.std(ddof=1) * np.sqrt(252))
    sharpe = sharpe_ratio(portfolio_returns)
    max_dd = max_drawdown(portfolio_returns)

    return {
        "snapshot_id": snap.id,
        "volatility": round(volatility, 4),
        "sharpe": round(sharpe, 4),
        "max_dd": round(max_dd, 4),
        "period_days": min_len,
    }
