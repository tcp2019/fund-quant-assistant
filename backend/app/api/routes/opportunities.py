from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.api.deps import get_db
from app.schemas.opportunities import OpportunitiesOut
from app.services.opportunities import build_opportunities

router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


@router.get("", response_model=OpportunitiesOut)
def list_opportunities(
    sell_limit: int = Query(default=5, ge=1, le=20),
    buy_limit: int = Query(default=5, ge=1, le=20),
    explore_limit: int = Query(default=5, ge=1, le=20),
    theme_limit: int = Query(default=5, ge=1, le=20),
    session: Session = Depends(get_db),
):
    return build_opportunities(
        session,
        sell_limit=sell_limit,
        buy_limit=buy_limit,
        explore_limit=explore_limit,
        theme_limit=theme_limit,
    )
