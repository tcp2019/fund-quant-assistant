from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_db
from app.schemas.analysis import CorrelationOut, RiskOut
from app.services.analysis import compute_correlation, compute_risk

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/correlation", response_model=CorrelationOut)
def correlation(session: Session = Depends(get_db)):
    return compute_correlation(session)


@router.get("/risk", response_model=RiskOut)
def risk(session: Session = Depends(get_db)):
    return compute_risk(session)
