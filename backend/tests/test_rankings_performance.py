import time

from sqlmodel import Session

from app.db.session import engine
from app.services.fund_catalog import load_catalog_fixture
from app.services.fund_rankings import (
    filter_rankings_for_category,
    filter_rankings_for_theme,
    load_catalog_lookup,
    load_rank_fixture,
)
from app.services.opportunities import build_opportunities
from app.services.theme_heat import rank_hot_themes


def test_filter_rankings_for_theme_under_200ms_with_fixture():
    with Session(engine) as session:
        load_catalog_fixture(session)
        rows = load_rank_fixture(session, "all_open", "fund_open_fund_rank_em_sample.json")
        lookup = load_catalog_lookup(session)
        start = time.perf_counter()
        filter_rankings_for_theme(
            session,
            "cpo_optics",
            rows,
            set(),
            limit=20,
            catalog_lookup=lookup,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
    assert elapsed_ms < 200


def test_rank_hot_themes_under_500ms_with_fixture():
    with Session(engine) as session:
        load_catalog_fixture(session)
        load_rank_fixture(session, "all_open", "fund_open_fund_rank_em_sample.json")
        lookup = load_catalog_lookup(session)
        rows = load_rank_fixture(session, "all_open", "fund_open_fund_rank_em_sample.json")
        start = time.perf_counter()
        ranked = rank_hot_themes(session, limit=5, catalog_lookup=lookup, open_rows=rows)
        elapsed_ms = (time.perf_counter() - start) * 1000
    assert len(ranked) >= 1
    assert elapsed_ms < 500


def test_build_opportunities_skips_hot_themes_when_disabled():
    with Session(engine) as session:
        result = build_opportunities(session, include_hot_themes=False)
    assert result.hot_themes == []
