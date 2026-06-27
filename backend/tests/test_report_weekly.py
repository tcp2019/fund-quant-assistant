from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_weekly_report_returns_markdown():
    response = client.get("/api/report/weekly")
    assert response.status_code == 200
    text = response.text
    assert "# 基金组合周报" in text


def test_weekly_report_with_snapshot_id():
    response = client.get("/api/report/weekly?snapshot_id=99999")
    assert response.status_code == 200
    text = response.text
    assert "# 基金组合周报" in text
