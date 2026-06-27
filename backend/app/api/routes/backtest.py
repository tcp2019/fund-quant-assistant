from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_db
from app.schemas.backtest import SensitivityReportOut, SnapshotStatsOut
from app.services.backtest.sensitivity import build_sensitivity_report, build_snapshot_stats
from app.services.backtest_engine import run_history_backtest

router = APIRouter(prefix="/api/backtest", tags=["backtest"])


@router.get("/sensitivity", response_model=SensitivityReportOut)
def sensitivity_report(session: Session = Depends(get_db)):
    return build_sensitivity_report(session)


@router.get("/snapshot-stats", response_model=SnapshotStatsOut)
def snapshot_stats(session: Session = Depends(get_db)):
    return build_snapshot_stats(session)


@router.post("/run")
def run_backtest(session: Session = Depends(get_db)):
    return run_history_backtest(session)
