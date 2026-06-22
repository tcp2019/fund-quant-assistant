from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from statistics import median

from sqlmodel import Session

from app.services.fund_catalog import load_catalog_lookup
from app.services.fund_rankings import (
    CatalogLookup,
    fetch_all_open_rankings,
    filter_rankings_for_theme,
)
from app.services.fund_themes import THEME_LABELS, fund_matches_theme

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


def _median_from_returns(returns: list[float]) -> float | None:
    if len(returns) < MIN_THEME_SAMPLE:
        return None
    top = sorted(returns, reverse=True)[:HEAT_SAMPLE_LIMIT]
    return float(median(top))


def _collect_theme_returns(
    rows: list[dict],
    catalog_lookup: CatalogLookup,
) -> dict[str, list[float]]:
    returns_by_theme: dict[str, list[float]] = defaultdict(list)
    for row in rows:
        return_1m = row.get("return_1m")
        if return_1m is None:
            continue
        name, fund_type = catalog_lookup.get(
            row["fund_code"],
            (row["fund_name"], ""),
        )
        for theme_id in THEME_LABELS:
            if fund_matches_theme(name, fund_type, theme_id):
                returns_by_theme[theme_id].append(float(return_1m))
    return returns_by_theme


def compute_theme_heat(
    session: Session,
    theme_id: str,
    *,
    catalog_lookup: CatalogLookup | None = None,
    open_rows: list[dict] | None = None,
) -> ThemeHeatRow | None:
    if theme_id not in THEME_LABELS:
        return None
    try:
        if open_rows is None:
            open_rows, _source = fetch_all_open_rankings(session)
        lookup = catalog_lookup if catalog_lookup is not None else load_catalog_lookup(session)
    except Exception:
        return None

    picked = filter_rankings_for_theme(
        session,
        theme_id,
        open_rows,
        exclude_codes=set(),
        limit=HEAT_SAMPLE_LIMIT,
        sort_by="return_1m",
        catalog_lookup=lookup,
    )
    returns = [row["return_1m"] for row in picked if row.get("return_1m") is not None]
    med = _median_from_returns(returns)
    if med is None:
        return None

    return ThemeHeatRow(
        theme=theme_id,
        label=THEME_LABELS[theme_id],
        heat_score=med,
        return_1m_median=med,
    )


def rank_hot_themes(
    session: Session,
    limit: int = 9,
    *,
    catalog_lookup: CatalogLookup | None = None,
    open_rows: list[dict] | None = None,
) -> list[ThemeHeatRow]:
    try:
        if open_rows is None:
            open_rows, _source = fetch_all_open_rankings(session)
        lookup = catalog_lookup if catalog_lookup is not None else load_catalog_lookup(session)
    except Exception:
        return []

    returns_by_theme = _collect_theme_returns(open_rows, lookup)
    rows: list[ThemeHeatRow] = []
    for theme_id, label in THEME_LABELS.items():
        med = _median_from_returns(returns_by_theme.get(theme_id, []))
        if med is None:
            continue
        rows.append(
            ThemeHeatRow(
                theme=theme_id,
                label=label,
                heat_score=med,
                return_1m_median=med,
            )
        )
    rows.sort(key=lambda item: item.heat_score, reverse=True)
    return rows[:limit]
