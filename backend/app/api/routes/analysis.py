import numpy as np
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_db
from app.db.models import Holding
from app.repositories.portfolio import get_latest_snapshot
from app.schemas.analysis import CorrelationOut, RiskOut
from app.services.analysis import (
    _aligned_nav_series,
    _returns_from_nav_series,
    compute_correlation,
    compute_risk,
)
from app.services.factor_style import compute_portfolio_style
from app.services.macro import fetch_macro_indicators
from app.services.optimizer import optimize_weights

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/correlation", response_model=CorrelationOut)
def correlation(session: Session = Depends(get_db)):
    return compute_correlation(session)


@router.get("/risk", response_model=RiskOut)
def risk(session: Session = Depends(get_db)):
    return compute_risk(session)


@router.get("/style-exposure")
def style_exposure(session: Session = Depends(get_db)):
    return compute_portfolio_style(session)


@router.get("/macro")
def macro_indicators():
    return fetch_macro_indicators()


@router.post("/optimize")
def optimize_portfolio(session: Session = Depends(get_db)):
    # Get NAV returns for current holdings
    snap = get_latest_snapshot(session)
    if not snap:
        return {"weights": None, "error": "无快照数据"}

    holdings = session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
    codes = [h.fund_code for h in holdings]

    if len(codes) < 2:
        return {"weights": [1.0] if codes else [], "error": None}

    labels, nav_series = _aligned_nav_series(session, codes, 252)
    returns_list = _returns_from_nav_series(nav_series)
    min_len = min(len(r) for r in returns_list)
    trimmed = np.column_stack([r[-min_len:] for r in returns_list])
    weights = optimize_weights(trimmed.T)

    if weights is not None:
        return {"weights": [round(float(w), 4) for w in weights], "codes": codes, "error": None}
    return {"weights": None, "codes": codes, "error": "优化未收敛或scipy不可用"}
