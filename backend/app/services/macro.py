"""Macro environment indicators via akshare."""

import logging

logger = logging.getLogger(__name__)


def classify_environment(bond_10y: float, bond_10y_60d_ago: float, shibor: float) -> str:
    """Classify macro environment as tight/neutral/loose."""
    rate_change = bond_10y - bond_10y_60d_ago
    if rate_change > 0.3 and shibor > 1.8:
        return "tight"
    elif rate_change < -0.3 and shibor < 1.5:
        return "loose"
    return "neutral"


def _bond_trend(bond_10y: float, bond_10y_60d: float) -> str:
    if bond_10y > bond_10y_60d + 0.1:
        return "rising"
    if bond_10y < bond_10y_60d - 0.1:
        return "falling"
    return "stable"


def _fetch_bond_10y_series():
    import akshare as ak

    try:
        df = ak.bond_zh_us_rate()
        column = "中国国债收益率10年"
        if column in df.columns:
            series = df[["日期", column]].dropna(subset=[column]).sort_values("日期")
            if not series.empty:
                return series, column
    except Exception as exc:
        logger.debug("bond_zh_us_rate unavailable: %s", exc)

    df = ak.bond_china_yield()
    if "10年期国债收益率" in df.columns:
        column = "10年期国债收益率"
        series = df[["日期", column]].dropna(subset=[column]).sort_values("日期")
        if not series.empty:
            return series, column

    treasury = df[df["曲线名称"].astype(str).str.contains("国债", na=False)]
    column = "10年"
    if column in treasury.columns and not treasury.empty:
        series = treasury[["日期", column]].dropna(subset=[column]).sort_values("日期")
        if not series.empty:
            return series, column

    raise KeyError("10-year government bond yield column not found")


def _fetch_shibor_overnight() -> float:
    import akshare as ak

    try:
        df = ak.macro_china_shibor_all()
        column = "O/N-定价"
        if column in df.columns and not df.empty:
            latest = df.sort_values("日期").iloc[-1][column]
            return float(latest)
    except Exception as exc:
        logger.debug("macro_china_shibor_all unavailable: %s", exc)

    if hasattr(ak, "shibor_rate"):
        df = ak.shibor_rate()
        if not df.empty and "利率" in df.columns:
            return float(df.iloc[0]["利率"])

    return 1.5


def fetch_macro_indicators() -> dict:
    """Fetch current macro indicators. Returns dict with:
    bond_10y, bond_10y_trend, shibor_overnight, environment, available
    """
    try:
        bond_series, _column = _fetch_bond_10y_series()
        bond_10y = float(bond_series.iloc[-1].iloc[1])
        bond_10y_60d = (
            float(bond_series.iloc[-60].iloc[1]) if len(bond_series) >= 60 else bond_10y
        )
        shibor_on = _fetch_shibor_overnight()
        env = classify_environment(bond_10y, bond_10y_60d, shibor_on)

        return {
            "bond_10y": round(bond_10y, 2),
            "bond_10y_trend": _bond_trend(bond_10y, bond_10y_60d),
            "shibor_overnight": round(shibor_on, 2),
            "environment": env,
            "available": True,
        }
    except Exception as exc:
        logger.warning("Failed to fetch macro indicators: %s", exc)
        return {"available": False, "environment": "unknown"}
