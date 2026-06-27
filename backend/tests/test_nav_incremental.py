from unittest.mock import patch
from sqlmodel import Session
from app.db.models import FundNavHistory
from app.services.data_sync import sync_fund_nav


def test_sync_nav_incremental_skips_existing_dates(session: Session):
    existing = FundNavHistory(code="110011", date="2026-06-25", nav=1.5, acc_nav=1.5)
    session.add(existing)
    session.commit()

    mock_nav_data = [
        {"date": "2026-06-24", "nav": 1.48, "acc_nav": 1.48},
        {"date": "2026-06-25", "nav": 1.55, "acc_nav": 1.55},
        {"date": "2026-06-26", "nav": 1.52, "acc_nav": 1.52},
    ]

    with patch("app.services.data_sync.fetch_nav_from_akshare") as mock_fetch:
        mock_fetch.return_value = mock_nav_data
        synced = sync_fund_nav(session, "110011")

    assert synced == 1  # only 2026-06-26 is new


def test_sync_nav_full_on_first_sync(session: Session):
    mock_nav_data = [
        {"date": "2026-06-24", "nav": 1.48, "acc_nav": 1.48},
        {"date": "2026-06-25", "nav": 1.55, "acc_nav": 1.55},
    ]

    with patch("app.services.data_sync.fetch_nav_from_akshare") as mock_fetch:
        mock_fetch.return_value = mock_nav_data
        synced = sync_fund_nav(session, "110011")

    assert synced == 2  # all rows are new (no existing data)
