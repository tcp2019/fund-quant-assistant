from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.db.models import FundMetadata, FundMetricsCache, FundNavHistory, Holding, PortfolioSnapshot
from app.db.session import engine
from app.main import app
from app.services.data_sync import sync_fund_metadata, sync_fund_nav, sync_portfolio_funds
from app.services.fund_classifier import classify_fund

client = TestClient(app)


def test_classify_fund():
    assert classify_fund("易方达优质精选混合", "混合型") == "stock"
    assert classify_fund("华夏债券A", "债券型") == "bond"
    assert classify_fund("某某FOF", "FOF") == "other"


def test_sync_fund_nav_mock(monkeypatch):
    def fake_fetch(code: str):
        return [{"date": "2025-06-01", "nav": 1.8, "acc_nav": 1.8}]

    monkeypatch.setattr("app.services.data_sync.fetch_nav_from_akshare", fake_fetch)

    with Session(engine) as session:
        count = sync_fund_nav(session, "110011")
        assert count == 1

        rows = session.exec(
            select(FundNavHistory).where(FundNavHistory.code == "110011")
        ).all()
        assert len(rows) == 1
        assert rows[0].date == "2025-06-01"
        assert rows[0].nav == 1.8
        assert rows[0].acc_nav == 1.8


def test_sync_fund_metadata_mock(monkeypatch):
    def fake_metadata(code: str):
        return {
            "name": "测试混合基金",
            "fund_type": "混合型",
            "manager": "张三",
            "benchmark_code": "沪深300",
        }

    monkeypatch.setattr("app.services.data_sync.fetch_metadata_from_akshare", fake_metadata)

    with Session(engine) as session:
        record = sync_fund_metadata(session, "110011")
        assert record.code == "110011"
        assert record.name == "测试混合基金"
        assert record.category == "stock"
        assert record.manager == "张三"


def test_sync_portfolio_funds_mock(monkeypatch):
    def fake_fetch(code: str):
        rows = []
        for day in range(1, 261):
            month = (day - 1) // 28 + 1
            dom = (day - 1) % 28 + 1
            nav = 1.0 + day * 0.001
            rows.append(
                {
                    "date": f"2024-{month:02d}-{dom:02d}",
                    "nav": nav,
                    "acc_nav": nav,
                }
            )
        return rows

    def fake_metadata(code: str):
        return {
            "name": "测试基金",
            "fund_type": "股票型",
            "manager": "李四",
            "benchmark_code": "中证500",
        }

    def fake_purchase_limits():
        return {
            "110011": {
                "purchase_status": "开放申购",
                "purchase_min_amount": 10.0,
                "daily_purchase_limit": 1e11,
            }
        }

    monkeypatch.setattr("app.services.data_sync.fetch_nav_from_akshare", fake_fetch)
    monkeypatch.setattr("app.services.data_sync.fetch_metadata_from_akshare", fake_metadata)
    monkeypatch.setattr(
        "app.services.data_sync.fetch_purchase_limits_from_akshare",
        fake_purchase_limits,
    )

    with Session(engine) as session:
        snap = PortfolioSnapshot(source="manual")
        session.add(snap)
        session.commit()
        session.refresh(snap)
        session.add(
            Holding(
                snapshot_id=snap.id,
                fund_code="110011",
                fund_name="易方达优质精选",
                shares=1000,
                cost_price=1.5,
                market_value=1800,
            )
        )
        session.commit()

        result = sync_portfolio_funds(session)
        assert result["synced"] == 1
        assert result["codes"] == ["110011"]

        nav_rows = session.exec(
            select(FundNavHistory).where(FundNavHistory.code == "110011")
        ).all()
        assert len(nav_rows) == 260

        meta = session.get(FundMetadata, "110011")
        assert meta is not None
        assert meta.category == "stock"
        assert meta.purchase_status == "开放申购"
        assert meta.daily_purchase_limit == 1e11

        metrics = session.exec(
            select(FundMetricsCache).where(FundMetricsCache.code == "110011")
        ).first()
        assert metrics is not None
        assert metrics.computed_from == "nav_history"


def test_api_data_sync(monkeypatch):
    def fake_fetch(code: str):
        return [{"date": "2025-06-01", "nav": 1.5, "acc_nav": 1.5}]

    def fake_metadata(code: str):
        return {
            "name": "测试基金",
            "fund_type": "货币型",
            "manager": "王五",
            "benchmark_code": "",
        }

    monkeypatch.setattr("app.services.data_sync.fetch_nav_from_akshare", fake_fetch)
    monkeypatch.setattr("app.services.data_sync.fetch_metadata_from_akshare", fake_metadata)
    monkeypatch.setattr("app.services.data_sync.fetch_purchase_limits_from_akshare", lambda: {})

    payload = {
        "holdings": [
            {
                "fund_code": "000001",
                "fund_name": "华夏成长",
                "shares": 500,
                "cost_price": 1.0,
                "market_value": 600,
                "profit": 100,
                "profit_rate": 0.2,
                "platform": "alipay",
            }
        ],
        "source": "manual",
    }
    client.post("/api/portfolio/snapshots", json=payload)

    resp = client.post("/api/data/sync")
    assert resp.status_code == 200
    data = resp.json()
    assert data["synced"] == 1
    assert "000001" in data["codes"]
