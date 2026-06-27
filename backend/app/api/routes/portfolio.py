from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.api.deps import get_db
from app.repositories import portfolio as repo
from app.schemas.portfolio import DailyHistoryOut, OverviewOut, SnapshotCreate, SnapshotsListOut

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("/overview", response_model=OverviewOut)
def overview(session: Session = Depends(get_db)):
    return repo.build_overview(session)


@router.get("/holdings", response_model=OverviewOut)
def holdings(session: Session = Depends(get_db)):
    return repo.build_overview(session)


@router.get("/daily-history", response_model=DailyHistoryOut)
def daily_history(days: int = 30, session: Session = Depends(get_db)):
    clamped = max(7, min(days, 90))
    return repo.build_daily_history(session, days=clamped)


@router.get("/snapshots", response_model=SnapshotsListOut)
def list_snapshots(session: Session = Depends(get_db)):
    return SnapshotsListOut(snapshots=repo.list_snapshots(session))


@router.post("/snapshots", status_code=201)
def create_snapshot(data: SnapshotCreate, session: Session = Depends(get_db)):
    snap = repo.create_snapshot(session, data)
    return {"snapshot_id": snap.id}
