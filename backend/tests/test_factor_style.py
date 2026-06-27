from app.services.factor_style import classify_fund_style


def test_large_cap_value():
    r = classify_fund_style("易方达沪深300价值ETF联接", "stock")
    assert r["size"] == "large_cap"
    assert r["style"] == "value"


def test_small_cap_growth():
    r = classify_fund_style("天弘创业板成长ETF联接", "stock")
    assert r["size"] == "small_cap"
    assert r["style"] == "growth"


def test_balanced():
    r = classify_fund_style("兴全合润混合", "stock")
    assert r["size"] == "balanced"
    assert r["style"] == "balanced"


def test_bond_fund():
    r = classify_fund_style("易方达纯债债券", "bond")
    assert r["size"] == "balanced"
    assert r["style"] == "balanced"
