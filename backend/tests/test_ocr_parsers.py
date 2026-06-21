from pathlib import Path

from app.services.ocr.parsers.alipay import parse_alipay_text
from app.services.ocr.parsers.tiantian import parse_tiantian_text

FIXTURES = Path(__file__).parent / "fixtures" / "ocr"


def test_parse_alipay():
    text = (FIXTURES / "alipay_sample.txt").read_text(encoding="utf-8")
    rows = parse_alipay_text(text)
    assert len(rows) == 1
    assert rows[0].fund_code == "110011"
    assert rows[0].shares == 1000.0
    assert rows[0].market_value == 1800.0


def test_parse_tiantian():
    text = (FIXTURES / "tiantian_sample.txt").read_text(encoding="utf-8")
    rows = parse_tiantian_text(text)
    assert rows[0].fund_code == "110011"
    assert rows[0].cost_price == 1.5
