from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_style_exposure_empty():
    response = client.get("/api/analysis/style-exposure")
    assert response.status_code == 200
    data = response.json()
    assert "size_exposure" in data
