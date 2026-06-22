from sqlmodel import Session

from app.schemas.funds import FundCandidateOut
from app.services.fund_rankings import (
    DEFAULT_SORT_FIELD,
    fetch_all_open_rankings,
    fetch_rankings,
    filter_rankings_for_category,
    filter_rankings_for_theme,
)
from app.services.fund_themes import THEME_LABELS


def _candidate_from_row(row: dict, category: str, source: str) -> FundCandidateOut:
    return FundCandidateOut(
        fund_code=row["fund_code"],
        fund_name=row["fund_name"],
        category=category,
        return_1y=row.get("return_1y"),
        return_1m=row.get("return_1m"),
        return_1w=row.get("return_1w"),
        as_of_date=row.get("as_of_date") or "",
        data_source=source,
    )


def recommend_funds(
    session: Session,
    category: str,
    exclude_codes: set[str] | list[str],
    limit: int = 3,
    sort_by: str = DEFAULT_SORT_FIELD,
) -> list[FundCandidateOut]:
    if category == "other":
        return []

    excluded = set(exclude_codes)
    try:
        rows, source = fetch_rankings(session, category)
    except Exception:
        return []

    picked = filter_rankings_for_category(
        session, category, rows, excluded, limit=limit, sort_by=sort_by
    )
    return [_candidate_from_row(row, category, source) for row in picked]


def recommend_funds_by_theme(
    session: Session,
    theme_id: str,
    exclude_codes: set[str] | list[str],
    limit: int = 3,
    sort_by: str = DEFAULT_SORT_FIELD,
) -> list[FundCandidateOut]:
    if theme_id not in THEME_LABELS:
        return []

    excluded = set(exclude_codes)
    try:
        rows, source = fetch_all_open_rankings(session)
    except Exception:
        return []

    picked = filter_rankings_for_theme(
        session, theme_id, rows, excluded, limit=limit, sort_by=sort_by
    )
    return [_candidate_from_row(row, theme_id, source) for row in picked]
