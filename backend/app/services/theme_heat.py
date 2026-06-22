from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from sqlmodel import Session

from app.services.fund_rankings import fetch_all_open_rankings, filter_rankings_for_theme
from app.services.fund_themes import THEME_LABELS

THEME_TO_CATEGORY: dict[str, str] = {
    "storage_semiconductor": "stock",
    "cpo_optics": "stock",
    "ai_compute": "stock",
    "new_energy": "stock",
    "healthcare": "stock",
    "consumer": "stock",
    "dividend": "stock",
    "gold": "gold",
    "qdii": "qdii",
}

MIN_THEME_SAMPLE = 3
HEAT_SAMPLE_LIMIT = 20


@dataclass(frozen=True)
class ThemeHeatRow:
    theme: str
    label: str
    heat_score: float
    return_1m_median: float


def compute_theme_heat(session: Session, theme_id: str) -> ThemeHeatRow | None:
    if theme_id not in THEME_LABELS:
        return None
    try:
        rows, _source = fetch_all_open_rankings(session)
    except Exception:
        return None

    picked = filter_rankings_for_theme(
        session,
        theme_id,
        rows,
        exclude_codes=set(),
        limit=HEAT_SAMPLE_LIMIT,
        sort_by="return_1m",
    )
    returns = [row["return_1m"] for row in picked if row.get("return_1m") is not None]
    if len(returns) < MIN_THEME_SAMPLE:
        return None

    med = float(median(returns))
    return ThemeHeatRow(
        theme=theme_id,
        label=THEME_LABELS[theme_id],
        heat_score=med,
        return_1m_median=med,
    )


def rank_hot_themes(session: Session, limit: int = 9) -> list[ThemeHeatRow]:
    rows: list[ThemeHeatRow] = []
    for theme_id in THEME_LABELS:
        heat = compute_theme_heat(session, theme_id)
        if heat is not None:
            rows.append(heat)
    rows.sort(key=lambda item: item.heat_score, reverse=True)
    return rows[:limit]
