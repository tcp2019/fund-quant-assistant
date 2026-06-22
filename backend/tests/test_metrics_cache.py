import numpy as np
from sqlmodel import Session, select

from app.db.models import FundMetricsCache, FundNavHistory
from app.db.session import engine
from app.services.metrics_cache import compute_and_cache_metrics


def _seed_nav_series(session: Session, code: str, count: int = 260) -> None:
    navs = 1.0 + np.cumsum(np.linspace(0.0005, 0.002, count))
    for index, nav in enumerate(navs):
        month = (index // 28) + 1
        day = (index % 28) + 1
        session.add(
            FundNavHistory(
                code=code,
                date=f"2024-{month:02d}-{day:02d}",
                nav=float(nav),
                acc_nav=float(nav),
            )
        )
    session.commit()


def test_compute_and_cache_metrics():
    with Session(engine) as session:
        _seed_nav_series(session, "110011")
        record = compute_and_cache_metrics(session, "110011")
        assert record is not None
        assert record.computed_from == "nav_history"
        assert record.sharpe_1y is not None
        assert record.return_1y is not None

        cached = session.exec(
            select(FundMetricsCache).where(FundMetricsCache.code == "110011")
        ).first()
        assert cached is not None
        assert cached.computed_from == "nav_history"


def test_compute_and_cache_metrics_insufficient_nav():
    with Session(engine) as session:
        session.add(
            FundNavHistory(code="000001", date="2025-01-01", nav=1.0, acc_nav=1.0)
        )
        session.commit()
        assert compute_and_cache_metrics(session, "000001") is None
