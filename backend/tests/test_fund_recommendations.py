from sqlmodel import Session

from app.db.session import engine
from app.services.fund_catalog import load_catalog_fixture
from app.services.fund_rankings import load_rank_fixture
from app.services.fund_recommendations import recommend_funds


def test_recommend_funds_bond():
    with Session(engine) as session:
        load_catalog_fixture(session)
        load_rank_fixture(session, "bond", "fund_open_fund_rank_em_sample.json")

        candidates = recommend_funds(session, "bond", exclude_codes=set(), limit=3)
        assert len(candidates) == 1
        assert candidates[0].fund_code == "050027"
        assert candidates[0].data_source == "akshare_open_fund_rank"
        assert candidates[0].return_1y == 8.5


def test_recommend_funds_money():
    with Session(engine) as session:
        load_rank_fixture(session, "money", "fund_money_rank_em_sample.json")
        candidates = recommend_funds(session, "money", exclude_codes=set(), limit=2)
        assert len(candidates) == 2
        assert candidates[0].data_source == "akshare_money_rank"


def test_recommend_funds_other_returns_empty():
    with Session(engine) as session:
        assert recommend_funds(session, "other", exclude_codes=set()) == []
