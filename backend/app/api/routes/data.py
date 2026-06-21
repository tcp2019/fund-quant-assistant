from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_db
from app.services.data_sync import sync_portfolio_funds
from app.services.signals.engine import run_signal_engine

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/sync")
def sync_data(session: Session = Depends(get_db)):
    result = sync_portfolio_funds(session)
    signals = run_signal_engine(session)
    result["signals_count"] = len(signals)
    return result
