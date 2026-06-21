from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_db
from app.services.data_sync import sync_portfolio_funds

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/sync")
def sync_data(session: Session = Depends(get_db)):
    return sync_portfolio_funds(session)
