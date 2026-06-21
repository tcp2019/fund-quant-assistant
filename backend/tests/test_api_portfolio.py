from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_overview_empty():
    resp = client.get("/api/portfolio/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_value"] == 0
    assert data["holdings"] == []


def test_create_snapshot_and_overview():
    payload = {
        "holdings": [
            {
                "fund_code": "110011",
                "fund_name": "易方达优质精选",
                "shares": 1000,
                "cost_price": 1.5,
                "market_value": 1800,
                "profit": 300,
                "profit_rate": 0.2,
                "platform": "alipay",
            }
        ],
        "source": "manual",
    }
    resp = client.post("/api/portfolio/snapshots", json=payload)
    assert resp.status_code == 201

    overview = client.get("/api/portfolio/overview").json()
    assert overview["total_value"] == 1800
    assert overview["total_cost"] == 1500
    assert overview["total_profit"] == 300
    assert len(overview["holdings"]) == 1
    assert overview["holdings"][0]["weight_pct"] == 100.0
