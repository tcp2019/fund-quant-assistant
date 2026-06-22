from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_db
from app.schemas.backtest import SensitivityReportOut, SnapshotStatsOut
from app.services.backtest.sensitivity import build_sensitivity_report, build_snapshot_stats

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.get("/sensitivity", response_model=SensitivityReportOut)
def sensitivity_report(session: Session = Depends(get_db)):
    return build_sensitivity_report(session)


@router.get("/snapshot-stats", response_model=SnapshotStatsOut)
def snapshot_stats(session: Session = Depends(get_db)):
    return build_snapshot_stats(session)
