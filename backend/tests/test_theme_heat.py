from statistics import median

from sqlmodel import Session

from app.db.session import engine
from app.services.fund_catalog import load_catalog_fixture
from app.services.fund_rankings import load_rank_fixture
from app.services.theme_heat import THEME_TO_CATEGORY, compute_theme_heat, rank_hot_themes


def test_theme_to_category_mapping():
    assert THEME_TO_CATEGORY["cpo_optics"] == "stock"
    assert THEME_TO_CATEGORY["qdii"] == "qdii"


def test_compute_theme_heat_cpo():
    with Session(engine) as session:
        load_catalog_fixture(session)
        load_rank_fixture(session, "all_open", "fund_open_fund_rank_em_sample.json")
        heat = compute_theme_heat(session, "cpo_optics")
    assert heat is not None
    assert heat.return_1m_median == 12.5
    assert heat.heat_score == 12.5


def test_rank_hot_themes_sorted():
    with Session(engine) as session:
        load_catalog_fixture(session)
        load_rank_fixture(session, "all_open", "fund_open_fund_rank_em_sample.json")
        ranked = rank_hot_themes(session, limit=3)
    assert len(ranked) >= 1
    scores = [row.heat_score for row in ranked]
    assert scores == sorted(scores, reverse=True)
