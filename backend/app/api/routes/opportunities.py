from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.deps import get_db
from app.schemas.opportunities import HotThemeOut, OpportunitiesOut
from app.services.opportunities import build_hot_themes_for_snapshot, build_opportunities

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


@router.get("", response_model=OpportunitiesOut)
def list_opportunities(
    sell_limit: int = Query(default=5, ge=1, le=20),
    buy_limit: int = Query(default=5, ge=1, le=20),
    explore_limit: int = Query(default=5, ge=1, le=20),
    theme_limit: int = Query(default=5, ge=1, le=20),
    include_hot_themes: bool = Query(default=True),
    include_theme_candidates: bool = Query(default=True),
    session: Session = Depends(get_db),
):
    return build_opportunities(
        session,
        sell_limit=sell_limit,
        buy_limit=buy_limit,
        explore_limit=explore_limit,
        theme_limit=theme_limit,
        include_hot_themes=include_hot_themes,
        include_theme_candidates=include_theme_candidates,
    )


@router.get("/hot-themes", response_model=list[HotThemeOut])
def list_hot_themes(
    theme_limit: int = Query(default=5, ge=1, le=20),
    include_candidates: bool = Query(default=False),
    session: Session = Depends(get_db),
):
    return build_hot_themes_for_snapshot(
        session,
        theme_limit=theme_limit,
        include_candidates=include_candidates,
    )
