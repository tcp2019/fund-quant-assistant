from sqlmodel import Session

from app.db.session import engine
from app.services.fund_catalog import load_catalog_fixture
from app.services.fund_rankings import load_rank_fixture
from app.services.fund_recommendations import recommend_funds_by_theme


def test_recommend_funds_by_theme_cpo():
    with Session(engine) as session:
        load_catalog_fixture(session)
        load_rank_fixture(session, "all_open", "fund_open_fund_rank_em_sample.json")

        candidates = recommend_funds_by_theme(
            session,
            "cpo_optics",
            exclude_codes=set(),
            limit=3,
            sort_by="return_1m",
        )
        assert len(candidates) == 1
        assert candidates[0].fund_code == "159583"
        assert candidates[0].return_1m == 12.5


def test_recommend_funds_by_theme_unknown():
    with Session(engine) as session:
        assert recommend_funds_by_theme(session, "unknown_theme", exclude_codes=set()) == []
