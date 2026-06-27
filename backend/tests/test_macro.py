from app.services.macro import classify_environment, fetch_macro_indicators


def test_rising_yields_tight():
    assert classify_environment(3.5, 2.8, 2.0) == "tight"


def test_falling_yields_loose():
    assert classify_environment(2.5, 3.0, 1.0) == "loose"


def test_stable_neutral():
    assert classify_environment(2.85, 2.80, 1.5) == "neutral"


def test_small_change_neutral():
    assert classify_environment(2.85, 2.70, 1.6) == "neutral"


def test_fetch_macro_indicators_uses_updated_akshare_columns(monkeypatch):
    import pandas as pd

    bond_df = pd.DataFrame(
        {
            "日期": [f"2026-0{i}-01" for i in range(1, 7)],
            "中国国债收益率10年": [2.0 + i * 0.01 for i in range(6)],
        }
    )
    shibor_df = pd.DataFrame({"日期": ["2026-06-26"], "O/N-定价": [1.37]})

    monkeypatch.setattr(
        "app.services.macro._fetch_bond_10y_series",
        lambda: (bond_df, "中国国债收益率10年"),
    )
    monkeypatch.setattr("app.services.macro._fetch_shibor_overnight", lambda: 1.37)

    result = fetch_macro_indicators()
    assert result["available"] is True
    assert result["bond_10y"] == 2.05
    assert result["shibor_overnight"] == 1.37
    assert result["environment"] == "neutral"
