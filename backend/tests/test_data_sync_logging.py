import json
from unittest.mock import patch

from sqlmodel import Session, select

from app.db.models import FundMetadata, Holding, PortfolioSnapshot, SyncLog
from app.services.data_sync import sync_portfolio_funds


def _seed_holdings(session: Session):
    snap = PortfolioSnapshot()
    session.add(snap)
    session.commit()

    holdings = [
        Holding(
            snapshot_id=snap.id,
            fund_code="110011",
            fund_name="易方达优质精选",
            shares=100,
            cost_price=1.5,
            market_value=150,
        ),
        Holding(
            snapshot_id=snap.id,
            fund_code="000001",
            fund_name="测试基金A",
            shares=50,
            cost_price=1.0,
            market_value=50,
        ),
    ]
    for h in holdings:
        session.add(h)
    session.commit()
    return snap


def _seed_metadata(session: Session, code: str, name: str):
    meta = session.get(FundMetadata, code)
    if meta is None:
        meta = FundMetadata(
            code=code,
            name=name,
            fund_type="",
            category="stock",
        )
        session.add(meta)
        session.commit()


def test_sync_writes_sync_log_on_success(session):
    snap = _seed_holdings(session)
    _seed_metadata(session, "110011", "易方达优质精选")
    _seed_metadata(session, "000001", "测试基金A")

    with patch(
        "app.services.data_sync.fetch_metadata_from_akshare"
    ) as mock_meta, patch(
        "app.services.data_sync.fetch_purchase_limits_from_akshare"
    ) as mock_limits, patch(
        "app.services.data_sync.fetch_nav_from_akshare"
    ) as mock_nav:
        mock_meta.return_value = {
            "name": "测试基金",
            "fund_type": "混合型",
            "manager": "测试经理",
            "benchmark_code": "000300",
        }
        mock_limits.return_value = {}
        mock_nav.return_value = [{"date": "2026-01-01", "nav": 1.0, "acc_nav": 1.0}]
        result = sync_portfolio_funds(session)

    assert result["synced"] >= 1

    log = session.exec(select(SyncLog).order_by(SyncLog.id.desc())).first()
    assert log is not None
    assert log.status in ("done", "partial")
    assert log.total_funds >= 1
    assert log.success_funds >= 1


def test_sync_log_records_nav_error(session):
    snap = _seed_holdings(session)
    _seed_metadata(session, "110011", "易方达优质精选")

    with patch(
        "app.services.data_sync.fetch_metadata_from_akshare"
    ) as mock_meta, patch(
        "app.services.data_sync.fetch_purchase_limits_from_akshare"
    ) as mock_limits, patch(
        "app.services.data_sync.fetch_nav_from_akshare"
    ) as mock_nav:
        mock_meta.return_value = {
            "name": "测试基金",
            "fund_type": "混合型",
            "manager": "测试经理",
            "benchmark_code": "000300",
        }
        mock_limits.return_value = {}
        mock_nav.side_effect = RuntimeError("AKShare rate limited")
        result = sync_portfolio_funds(session)

    log = session.exec(select(SyncLog).order_by(SyncLog.id.desc())).first()
    assert log is not None
    errors = json.loads(log.errors_json)
    assert any(e["fund_code"] == "110011" and "nav" in e["stage"] for e in errors)
