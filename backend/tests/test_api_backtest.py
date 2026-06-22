from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_backtest_sensitivity_empty():
    resp = client.get("/api/backtest/sensitivity")
    assert resp.status_code == 200
    data = resp.json()
    assert "scenarios" in data


def test_backtest_snapshot_stats_empty():
    resp = client.get("/api/backtest/snapshot-stats")
    assert resp.status_code == 200
    assert "snapshots" in resp.json()
