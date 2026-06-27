import json
from datetime import datetime

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.models import SyncLog
from app.db.session import engine
from app.main import app

client = TestClient(app)


def test_list_sync_logs_empty():
    response = client.get("/api/settings/sync-logs")
    assert response.status_code == 200
    data = response.json()
    assert data["logs"] == []


def test_list_sync_logs_with_data():
    with Session(engine) as session:
        for status in ("done", "partial", "failed"):
            log = SyncLog(
                status=status,
                total_funds=5,
                success_funds=3,
                failed_funds=2,
                errors_json=json.dumps([]),
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
            )
            session.add(log)
        session.commit()

    response = client.get("/api/settings/sync-logs?limit=3")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["logs"], list)
    assert len(data["logs"]) == 3
    # Most recent first
    assert data["logs"][0]["status"] == "failed"
    assert data["logs"][1]["status"] == "partial"
    assert data["logs"][2]["status"] == "done"
    log0 = data["logs"][0]
    assert "id" in log0
    assert log0["total_funds"] == 5
    assert log0["errors_json"] == "[]"


def test_list_sync_logs_respects_limit():
    with Session(engine) as session:
        for _ in range(5):
            log = SyncLog(
                status="done",
                total_funds=3,
                success_funds=3,
                failed_funds=0,
                errors_json=json.dumps([]),
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
            )
            session.add(log)
        session.commit()

    response = client.get("/api/settings/sync-logs?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["logs"]) == 2
