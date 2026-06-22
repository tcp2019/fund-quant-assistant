from sqlmodel import Session

from app.db.session import engine
from app.services.fund_catalog import load_catalog_fixture, search_catalog


def test_search_catalog_by_name():
    with Session(engine) as session:
        load_catalog_fixture(session)
        results = search_catalog(session, "博时信用", limit=5)
        assert len(results) == 1
        assert results[0].code == "050027"


def test_search_catalog_by_code_prefix():
    with Session(engine) as session:
        load_catalog_fixture(session)
        results = search_catalog(session, "0129", limit=5)
        assert any(row.code == "012922" for row in results)
