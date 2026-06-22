from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.session import engine
from app.main import app
from app.services.fund_catalog import load_catalog_fixture

client = TestClient(app)


def test_search_funds_not_ready():
    resp = client.get("/api/funds/search", params={"q": "华夏"})
    assert resp.status_code == 503


def test_search_funds_with_catalog():
    with Session(engine) as session:
        load_catalog_fixture(session)

    resp = client.get("/api/funds/search", params={"q": "华夏"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["catalog_ready"] is True
    assert len(data["results"]) >= 1
    assert data["results"][0]["fund_code"] == "000001"


def test_refresh_catalog_mock(monkeypatch):
    import pandas as pd

    def fake_fund_name_em():
        return pd.DataFrame(
            [
                {
                    "基金代码": "110011",
                    "拼音缩写": "YFD",
                    "基金简称": "易方达优质精选",
                    "基金类型": "混合型",
                    "拼音全称": "YIFANGDA",
                }
            ]
        )

    monkeypatch.setattr("app.services.fund_catalog.ak.fund_name_em", fake_fund_name_em)
    resp = client.post("/api/funds/catalog/refresh")
    assert resp.status_code == 200
    assert resp.json()["count"] == 1

    search = client.get("/api/funds/search", params={"q": "易方达"})
    assert search.status_code == 200
    assert search.json()["results"][0]["fund_code"] == "110011"


def test_list_themes():
    resp = client.get("/api/funds/themes")
    assert resp.status_code == 200
    data = resp.json()
    assert any(item["theme"] == "cpo_optics" for item in data)


def test_theme_candidates_with_fixture():
    from app.services.fund_rankings import load_rank_fixture

    with Session(engine) as session:
        load_catalog_fixture(session)
        load_rank_fixture(session, "all_open", "fund_open_fund_rank_em_sample.json")

    resp = client.get("/api/funds/themes/cpo_optics/candidates", params={"sort_by": "return_1m"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["theme"] == "cpo_optics"
    assert len(data["candidates"]) >= 1
    assert data["candidates"][0]["fund_code"] == "159583"
