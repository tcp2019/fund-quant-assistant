import json
from typing import Any

import akshare as ak

from app.services.http_retry import with_retry as _with_retry

PEER_UNDERPERFORM_PERCENTILE = 25.0


def fetch_peer_return_percentile_3m(code: str) -> float | None:
    def _fetch() -> float | None:
        df = ak.fund_open_fund_info_em(symbol=code, indicator="同类排名百分比")
        if df is None or df.empty:
            return None
        column = "同类型排名-每日近3月收益排名百分比"
        if column not in df.columns:
            return None
        raw = df.iloc[-1][column]
        if raw != raw:
            return None
        return float(raw)

    try:
        return _with_retry(_fetch)
    except Exception:
        return None


def parse_user_themes(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return []
    return [item for item in parsed if isinstance(item, str)]


def merge_peer_into_metrics(metrics: dict[str, Any], peer_percentile: float | None) -> dict[str, Any]:
    if peer_percentile is not None:
        metrics["peer_return_percentile_3m"] = peer_percentile
        if metrics.get("excess_return_1y") is None and metrics.get("return_1y") is not None:
            # Approximate underperformance vs peers when benchmark excess is unavailable.
            peer_median_return = metrics["return_1y"]
            if peer_percentile < 50:
                gap = (50.0 - peer_percentile) / 100.0
                metrics["excess_return_1y"] = round(-gap * abs(metrics["return_1y"]), 4)
    return metrics
