from sqlmodel import Session

from app.services.fund_catalog import load_catalog_fixture
from app.services.fund_code_resolver import (
    imported_code_matches_name,
    resolve_fund_code_by_name,
    resolve_holdings_fund_codes,
)
from app.services.ocr.parsers.base import ParsedHolding


def test_resolve_fund_code_by_name_from_catalog(session: Session):
    load_catalog_fixture(session)
    code, official, score = resolve_fund_code_by_name(session, "易方达全球成长精选混合 (QDII) C")
    assert code == "012922"
    assert "易方达全球成长精选" in official
    assert score >= 0.9


def test_imported_code_mismatch_detected(session: Session):
    load_catalog_fixture(session)
    assert not imported_code_matches_name(session, "010688", "易方达全球成长精选混合 (QDII) C")
    assert imported_code_matches_name(session, "012922", "易方达全球成长精选混合(QDII)C")
    assert not imported_code_matches_name(session, "000307", "易方达黄金 ETF 联接 C")
    assert imported_code_matches_name(session, "002963", "易方达黄金ETF联接C")


def test_resolve_holdings_replaces_wrong_alipay_code(session: Session):
    load_catalog_fixture(session)
    holdings = [
        ParsedHolding(
            fund_code="010688",
            fund_name="易方达全球成长精选混合 (QDII) C",
            shares=0,
            cost_price=0,
            market_value=66337.88,
            profit=0,
            profit_rate=0,
            platform="alipay",
        ),
        ParsedHolding(
            fund_code="002963",
            fund_name="易方达黄金ETF联接C",
            shares=0,
            cost_price=0,
            market_value=1000,
            profit=0,
            profit_rate=0,
            platform="alipay",
        ),
    ]
    warnings = resolve_holdings_fund_codes(session, holdings)
    assert holdings[0].fund_code == "012922"
    assert holdings[1].fund_code == "002963"
    assert any("010688" in warning for warning in warnings)
