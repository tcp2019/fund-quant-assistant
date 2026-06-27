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


def fetch_macro_indicators() -> dict:
    """Fetch current macro indicators. Returns dict with:
    bond_10y, bond_10y_trend, shibor_overnight, environment, available
    """
    try:
        import akshare as ak

        bond_df = ak.bond_china_yield()
        bond_10y = float(bond_df.iloc[-1]["10年期国债收益率"])
        bond_10y_60d = float(bond_df.iloc[-60]["10年期国债收益率"]) if len(bond_df) >= 60 else bond_10y

        shibor_df = ak.shibor_rate()
        shibor_on = float(shibor_df.iloc[0]["利率"]) if len(shibor_df) > 0 else 1.5

        env = classify_environment(bond_10y, bond_10y_60d, shibor_on)

        trend = "stable"
        if bond_10y > bond_10y_60d + 0.1:
            trend = "rising"
        elif bond_10y < bond_10y_60d - 0.1:
            trend = "falling"

        return {
            "bond_10y": round(bond_10y, 2),
            "bond_10y_trend": trend,
            "shibor_overnight": round(shibor_on, 2),
            "environment": env,
            "available": True,
        }
    except Exception as exc:
        logger.warning("Failed to fetch macro indicators: %s", exc)
        return {"available": False, "environment": "unknown"}
