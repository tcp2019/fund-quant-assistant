from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_opportunities_empty_snapshot():
    resp = client.get("/api/opportunities")
    assert resp.status_code == 200
    data = resp.json()
    assert data["snapshot_id"] is None
    assert data["sell_actions"] == []
