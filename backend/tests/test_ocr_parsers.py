from pathlib import Path

from app.services.ocr.parsers.alipay import parse_alipay_text
from app.services.ocr.parsers.base import extract_fund_code
from app.services.ocr.parsers.tiantian import parse_tiantian_text

FIXTURES = Path(__file__).parent / "fixtures" / "ocr"


def test_parse_alipay():
    text = (FIXTURES / "alipay_sample.txt").read_text(encoding="utf-8")
    rows = parse_alipay_text(text)
    assert len(rows) == 1
    assert rows[0].fund_code == "110011"
    assert rows[0].shares == 1000.0
    assert rows[0].market_value == 1800.0


def test_parse_alipay_list_view():
    text = (FIXTURES / "alipay_list_sample.txt").read_text(encoding="utf-8")
    rows = parse_alipay_text(text)
    assert len(rows) >= 30
    assert rows[0].fund_name.startswith("易方达全球成长精选")
    assert rows[0].market_value == 62056.78
    assert rows[0].profit == 29496.78
    assert all(row.market_value > 0 for row in rows)


def test_extract_fund_code_ignores_amount_tail():
    assert extract_fund_code("6,217730.00") is None
    assert extract_fund_code("基金代码 110011 持有") == "110011"


def test_parse_alipay_merged_export():
    text = (FIXTURES / "alipay_merged_sample.txt").read_text(encoding="utf-8")
    rows = parse_alipay_text(text)
    assert len(rows) == 4
    assert rows[0].fund_code == "012422"
    assert rows[0].fund_name.startswith("国富全球股票优选")
    assert rows[0].market_value == 42036.78
    assert abs(rows[0].profit_rate - 0.907) < 0.001
    assert rows[2].fund_code == "011840"
    assert rows[2].profit_rate < 0


def test_parse_alipay_tab_export_with_spaces_and_category():
    text = (FIXTURES / "alipay_tab_export_sample.txt").read_text(encoding="utf-8")
    rows = parse_alipay_text(text)
    assert len(rows) == 4
    assert rows[0].fund_code == "012922"
    assert "易方达全球成长精选" in rows[0].fund_name
    assert rows[0].market_value == 62056.78
    assert abs(rows[0].profit_rate - 0.907) < 0.001
    assert rows[2].fund_code == "011840"
    assert rows[2].profit_rate == 0.0
    assert rows[3].fund_code == "014497"


def test_parse_alipay_tab_export_code_first_with_holding_profit():
    text = (FIXTURES / "alipay_tab_code_first_sample.txt").read_text(encoding="utf-8")
    rows = parse_alipay_text(text)
    assert len(rows) == 5
    assert rows[0].fund_code == "010688"
    assert "易方达全球成长精选" in rows[0].fund_name
    assert rows[0].market_value == 66337.88
    assert rows[0].profit == 33697.88
    assert rows[0].profit_rate > 1.0
    assert rows[-1].fund_code == "007466"
    assert "华泰柏瑞" in rows[-1].fund_name
    assert rows[-1].profit == -623.56
    assert rows[-1].profit_rate < 0


def test_parse_tiantian():
    text = (FIXTURES / "tiantian_sample.txt").read_text(encoding="utf-8")
    rows = parse_tiantian_text(text)
    assert rows[0].fund_code == "110011"
    assert rows[0].cost_price == 1.5
