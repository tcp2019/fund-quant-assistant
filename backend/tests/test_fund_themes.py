from app.services.fund_themes import (
    detect_themes,
    fund_matches_theme,
    primary_theme,
    theme_search_keywords,
)


def test_detect_storage_semiconductor_theme():
    themes = detect_themes("华夏国证半导体芯片ETF", "股票型")
    assert "storage_semiconductor" in themes


def test_detect_cpo_optics_theme():
    themes = detect_themes("富国中证通信设备主题ETF", "股票型")
    assert "cpo_optics" in themes


def test_primary_theme_priority():
    assert primary_theme("某某存储芯片混合", "混合型") == "storage_semiconductor"


def test_theme_search_aliases():
    assert theme_search_keywords("cpo") == ["CPO", "光模块", "通信设备", "光通信"]
    assert theme_search_keywords("存储") is not None


def test_fund_matches_theme():
    assert fund_matches_theme("通信设备主题ETF", "股票型", "cpo_optics")
    assert not fund_matches_theme("博时信用债券", "债券型", "cpo_optics")
