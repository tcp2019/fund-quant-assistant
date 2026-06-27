import json
from datetime import datetime

from app.db.models import SyncLog


def test_sync_log_create(session):
    log = SyncLog(
        status="partial",
        total_funds=5,
        success_funds=3,
        failed_funds=2,
        errors_json=json.dumps(
            [
                {"fund_code": "000001", "stage": "nav", "error": "timeout"},
                {"fund_code": "000002", "stage": "metadata", "error": "not found"},
            ]
        ),
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    assert log.id is not None
    assert log.status == "partial"
    assert log.total_funds == 5
    assert log.success_funds == 3
    assert log.failed_funds == 2

    errors = json.loads(log.errors_json)
    assert len(errors) == 2
    assert errors[0]["fund_code"] == "000001"


def test_sync_log_partial_details(session):
    log = SyncLog(
        status="failed",
        total_funds=3,
        success_funds=0,
        failed_funds=3,
        errors_json=json.dumps(
            [{"fund_code": "000001", "stage": "nav", "error": "network error"}]
        ),
        started_at=datetime.utcnow(),
        finished_at=datetime.utcnow(),
    )
    session.add(log)
    session.commit()

    assert log.status == "failed"
    assert log.success_funds == 0
