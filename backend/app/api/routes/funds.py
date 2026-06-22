from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from app.api.deps import get_db
from app.db.models import FundCatalog, Holding
from app.repositories.portfolio import get_latest_snapshot
from app.schemas.funds import (
    CatalogRefreshOut,
    FundSearchOut,
    FundSearchResultOut,
    ThemeCandidatesOut,
)
from app.services.fund_catalog import ensure_catalog, refresh_catalog, search_catalog
from app.services.fund_recommendations import recommend_funds_by_theme
from app.services.fund_themes import THEME_LABELS, THEME_SORT_FIELDS, theme_label

router = APIRouter(prefix="/api/funds", tags=["funds"])


@router.get("/search", response_model=FundSearchOut)
def search_funds(
    q: str = Query(min_length=1),
    limit: int = Query(default=8, ge=1, le=50),
    session: Session = Depends(get_db),
):
    total = session.exec(select(func.count()).select_from(FundCatalog)).one()
    if total == 0:
        raise HTTPException(status_code=503, detail="基金目录尚未就绪，请在设置页刷新基金目录")

    results = search_catalog(session, q, limit=limit)
    return FundSearchOut(
        catalog_ready=True,
        results=[
            FundSearchResultOut(
                fund_code=row.code,
                fund_name=row.name,
                fund_type=row.fund_type,
            )
            for row in results
        ],
    )


@router.get("/themes", response_model=list[dict[str, str]])
def list_themes():
    return [{"theme": theme_id, "label": label} for theme_id, label in THEME_LABELS.items()]


@router.get("/themes/{theme_id}/candidates", response_model=ThemeCandidatesOut)
def theme_candidates(
    theme_id: str,
    sort_by: str = Query(default="return_1m"),
    limit: int = Query(default=5, ge=1, le=20),
    session: Session = Depends(get_db),
):
    if theme_id not in THEME_LABELS:
        raise HTTPException(status_code=404, detail="未知主题")
    if sort_by not in THEME_SORT_FIELDS:
        raise HTTPException(status_code=400, detail=f"sort_by 必须是 {', '.join(THEME_SORT_FIELDS)}")

    snap = get_latest_snapshot(session)
    held_codes: set[str] = set()
    if snap:
        holdings = session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
        held_codes = {holding.fund_code for holding in holdings if holding.fund_code}

    candidates = recommend_funds_by_theme(
        session,
        theme_id,
        held_codes,
        limit=limit,
        sort_by=sort_by,
    )
    return ThemeCandidatesOut(
        theme=theme_id,
        label=theme_label(theme_id),
        sort_by=sort_by,
        candidates=candidates,
    )


@router.post("/catalog/refresh", response_model=CatalogRefreshOut)
def refresh_fund_catalog(session: Session = Depends(get_db)):
    try:
        count = refresh_catalog(session)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"刷新基金目录失败: {exc}") from exc
    return CatalogRefreshOut(count=count)
