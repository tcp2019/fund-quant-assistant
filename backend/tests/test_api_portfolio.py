from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_snapshots_empty():
    resp = client.get("/api/portfolio/snapshots")
    assert resp.status_code == 200
    assert resp.json()["snapshots"] == []


def test_list_snapshots_with_total_values():
    payload_a = {
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
    payload_b = {
        "holdings": [
            {
                "fund_code": "110011",
                "fund_name": "易方达优质精选",
                "shares": 1000,
                "cost_price": 1.5,
                "market_value": 2000,
                "profit": 500,
                "profit_rate": 0.25,
                "platform": "alipay",
            }
        ],
        "source": "ocr",
    }
    client.post("/api/portfolio/snapshots", json=payload_a)
    client.post("/api/portfolio/snapshots", json=payload_b)

    resp = client.get("/api/portfolio/snapshots")
    assert resp.status_code == 200
    snapshots = resp.json()["snapshots"]
    assert len(snapshots) == 2
    assert snapshots[0]["total_value"] == 2000
    assert snapshots[0]["source"] == "ocr"
    assert snapshots[1]["total_value"] == 1800
    assert snapshots[1]["source"] == "manual"
    assert "id" in snapshots[0]
    assert "created_at" in snapshots[0]


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
    assert overview["concentration_top5_pct"] == 100.0
    assert len(overview["top_holdings"]) == 1
    assert len(overview["category_allocation"]) == 1
    assert overview["category_allocation"][0]["category"] == "other"


def test_overview_holding_theme_tags():
    payload = {
        "holdings": [
            {
                "fund_code": "159583",
                "fund_name": "富国中证通信设备主题ETF",
                "shares": 1000,
                "cost_price": 1.0,
                "market_value": 1200,
                "profit": 200,
                "profit_rate": 0.2,
                "platform": "alipay",
            }
        ],
        "source": "manual",
    }
    client.post("/api/portfolio/snapshots", json=payload)
    overview = client.get("/api/portfolio/overview").json()
    themes = overview["holdings"][0]["themes"]
    assert any(item["theme"] == "cpo_optics" for item in themes)
    assert any("CPO" in item["label"] or "光通信" in item["label"] for item in themes)


def test_overview_category_allocation_and_concentration():
    payload = {
        "holdings": [
            {
                "fund_code": "110011",
                "fund_name": "易方达优质精选混合",
                "shares": 1000,
                "cost_price": 1.5,
                "market_value": 5000,
                "profit": 500,
                "profit_rate": 0.1,
                "platform": "alipay",
            },
            {
                "fund_code": "000001",
                "fund_name": "华夏债券A",
                "shares": 800,
                "cost_price": 1.2,
                "market_value": 3000,
                "profit": 100,
                "profit_rate": 0.03,
                "platform": "alipay",
            },
            {
                "fund_code": "050027",
                "fund_name": "博时信用债券",
                "shares": 600,
                "cost_price": 1.1,
                "market_value": 2000,
                "profit": 50,
                "profit_rate": 0.02,
                "platform": "alipay",
            },
        ],
        "source": "manual",
    }
    client.post("/api/portfolio/snapshots", json=payload)

    overview = client.get("/api/portfolio/overview").json()
    assert overview["total_value"] == 10000
    assert overview["concentration_top5_pct"] == 100.0
    assert len(overview["top_holdings"]) == 3
    assert overview["top_holdings"][0]["fund_code"] == "110011"
    assert overview["top_holdings"][0]["weight_pct"] == 50.0

    categories = {item["category"]: item["weight_pct"] for item in overview["category_allocation"]}
    assert categories["stock"] == 50.0
    assert categories["bond"] == 50.0


def test_overview_ocr_import_without_shares():
    payload = {
        "holdings": [
            {
                "fund_code": "012922",
                "fund_name": "易方达全球成长精选混合(QDII)C",
                "shares": 0,
                "cost_price": 32541.57,
                "market_value": 62056.78,
                "profit": 29515.21,
                "profit_rate": 0.907,
                "platform": "alipay",
            },
            {
                "fund_code": "016702",
                "fund_name": "银华海外数字经济量化选股混合(QDII)C",
                "shares": 0,
                "cost_price": 35930.65,
                "market_value": 43562.32,
                "profit": 7631.67,
                "profit_rate": 0.2124,
                "platform": "alipay",
            },
        ],
        "source": "ocr",
    }
    resp = client.post("/api/portfolio/snapshots", json=payload)
    assert resp.status_code == 201

    overview = client.get("/api/portfolio/overview").json()
    assert overview["total_value"] == 105619.1
    assert overview["total_cost"] == 68472.22
    assert overview["total_profit"] == 37146.88
    assert overview["total_profit_rate"] == round(37146.88 / 68472.22, 4)
