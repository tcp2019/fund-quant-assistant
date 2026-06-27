from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.models import SignalRecord, StrategyConfig
from app.db.session import engine
from app.main import app
from app.schemas.settings import DEFAULT_TEMPLATES, DEFAULT_THRESHOLDS

client = TestClient(app)


def test_get_strategy_seeds_balanced_default():
    resp = client.get("/api/settings/strategy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_name"] == "balanced"
    assert data["target_weights"] == DEFAULT_TEMPLATES["balanced"]
    assert data["thresholds"] == DEFAULT_THRESHOLDS

    with Session(engine) as session:
        config = session.exec(select(StrategyConfig)).first()
        assert config is not None
        assert config.template_name == "balanced"


def test_get_strategy_returns_existing():
    client.get("/api/settings/strategy")
    resp = client.get("/api/settings/strategy")
    assert resp.status_code == 200
    assert resp.json()["template_name"] == "balanced"


def test_put_strategy_updates_template():
    client.get("/api/settings/strategy")
    resp = client.put(
        "/api/settings/strategy",
        json={"template_name": "aggressive"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_name"] == "aggressive"
    assert data["target_weights"] == DEFAULT_TEMPLATES["aggressive"]


def test_put_strategy_custom_weights():
    client.get("/api/settings/strategy")
    custom_weights = {
        "stock": 0.50,
        "bond": 0.20,
        "money": 0.10,
        "qdii": 0.10,
        "other": 0.10,
    }
    resp = client.put(
        "/api/settings/strategy",
        json={
            "template_name": "custom",
            "target_weights": custom_weights,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["template_name"] == "custom"
    assert data["target_weights"] == custom_weights


def test_put_strategy_custom_weights_must_sum_to_one():
    client.get("/api/settings/strategy")
    resp = client.put(
        "/api/settings/strategy",
        json={
            "template_name": "custom",
            "target_weights": {
                "stock": 0.50,
                "bond": 0.20,
                "money": 0.10,
                "qdii": 0.10,
                "other": 0.05,
            },
        },
    )
    assert resp.status_code == 422


def test_put_strategy_intra_category_mode():
    client.get("/api/settings/strategy")
    resp = client.put(
        "/api/settings/strategy",
        json={"template_name": "balanced", "intra_category_mode": "pro_rata"},
    )
    assert resp.status_code == 200
    assert resp.json()["intra_category_mode"] == "pro_rata"


def test_put_strategy_custom_fund_weights_must_sum_to_one():
    client.get("/api/settings/strategy")
    resp = client.put(
        "/api/settings/strategy",
        json={
            "template_name": "balanced",
            "intra_category_mode": "custom",
            "fund_target_weights": {"110011": 0.6, "000001": 0.3},
        },
    )
    assert resp.status_code == 422


def test_put_strategy_updates_thresholds():
    client.get("/api/settings/strategy")
    resp = client.put(
        "/api/settings/strategy",
        json={
            "template_name": "balanced",
            "thresholds": {
                "rebalance_deviation_pct": 8.0,
                "rebalance_force_days": 365,
                "single_fund_max_pct": 30.0,
                "correlation_max": 0.85,
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["thresholds"]["rebalance_deviation_pct"] == 8.0
    assert data["thresholds"]["single_fund_max_pct"] == 30.0


def test_put_strategy_reruns_signal_engine():
    payload = {
        "holdings": [
            {
                "fund_code": "110011",
                "fund_name": "易方达优质精选",
                "shares": 1000,
                "cost_price": 1.5,
                "market_value": 8000,
                "profit": 500,
                "profit_rate": 0.1,
                "platform": "alipay",
            },
            {
                "fund_code": "000001",
                "fund_name": "华夏成长",
                "shares": 500,
                "cost_price": 2.0,
                "market_value": 2000,
                "profit": 100,
                "profit_rate": 0.05,
                "platform": "alipay",
            },
        ],
        "source": "manual",
    }
    client.post("/api/portfolio/snapshots", json=payload)
    client.get("/api/settings/strategy")

    resp = client.put(
        "/api/settings/strategy",
        json={
            "template_name": "conservative",
            "thresholds": {
                "rebalance_deviation_pct": 1.0,
                "rebalance_force_days": 365,
                "single_fund_max_pct": 25.0,
                "correlation_max": 0.85,
            },
        },
    )
    assert resp.status_code == 200

    with Session(engine) as session:
        records = session.exec(select(SignalRecord)).all()
        assert len(records) > 0


def test_llm_test_endpoint_no_key():
    from unittest.mock import patch

    with patch("app.api.routes.settings.test_llm_connection", return_value=(False, "未配置 API Key")):
        resp = client.post("/api/settings/llm/test", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"] == "未配置 API Key"


def test_llm_test_endpoint_success():
    from unittest.mock import AsyncMock, patch

    async def mock_test(**kwargs):
        return True, None

    with patch("app.api.routes.settings.test_llm_connection", new=AsyncMock(side_effect=mock_test)):
        resp = client.post(
            "/api/settings/llm/test",
            json={"api_key": "sk-test", "base_url": "https://api.deepseek.com", "model": "deepseek-v4-flash"},
        )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
