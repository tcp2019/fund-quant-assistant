import json
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import akshare as ak
import pandas as pd
from sqlmodel import Session, delete, select

from app.db.models import FundRankCache
from app.services.fund_catalog import get_catalog_entry
from app.services.fund_themes import fund_matches_theme

RANK_TTL_HOURS = 24
DEFAULT_SORT_FIELD = "return_1m"

MONEY_CATEGORY = "money"
OPEN_RANK_CATEGORIES = {"stock", "bond", "qdii", "gold", "other"}


def _parse_return_pct(raw: Any) -> float | None:
    if raw is None:
        return None
    if isinstance(raw, float) and math.isnan(raw):
        return None
    text = str(raw).strip().replace("%", "")
    if not text or text.lower() == "nan":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _dataframe_to_rank_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        return_1y = _parse_return_pct(row.get("近1年"))
        return_1m = _parse_return_pct(row.get("近1月"))
        return_1w = _parse_return_pct(row.get("近1周"))
        if return_1y is None and return_1m is None and return_1w is None:
            continue
        rows.append(
            {
                "fund_code": str(row["基金代码"]).zfill(6),
                "fund_name": str(row["基金简称"]),
                "as_of_date": str(row.get("日期") or ""),
                "return_1y": return_1y,
                "return_1m": return_1m,
                "return_1w": return_1w,
            }
        )
    return rows


def _fetch_open_fund_rankings() -> list[dict[str, Any]]:
    df = ak.fund_open_fund_rank_em()
    return _dataframe_to_rank_rows(df)


def _fetch_money_fund_rankings() -> list[dict[str, Any]]:
    df = ak.fund_money_rank_em()
    return _dataframe_to_rank_rows(df)


def _load_fixture(name: str) -> list[dict[str, Any]]:
    path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "akshare" / name
    df = pd.DataFrame(json.loads(path.read_text(encoding="utf-8")))
    return _dataframe_to_rank_rows(df)


def _matches_category(
    session: Session,
    category: str,
    fund_code: str,
    fund_name: str,
) -> bool:
    entry = get_catalog_entry(session, fund_code)
    fund_type = entry.fund_type if entry else ""
    name = entry.name if entry else fund_name
    text = f"{name}{fund_type}"

    if category == "stock":
        return any(keyword in text for keyword in ("股票", "混合", "指数"))
    if category == "bond":
        return "债券" in text
    if category == "money":
        return "货币" in text
    if category == "qdii":
        return "QDII" in text.upper() or "qdii" in text.lower()
    if category == "gold":
        return "黄金" in text
    return category == "other"


def _cache_is_fresh(record: FundRankCache | None) -> bool:
    if record is None:
        return False
    return datetime.utcnow() - record.fetched_at < timedelta(hours=RANK_TTL_HOURS)


def fetch_rankings(session: Session, category: str) -> tuple[list[dict[str, Any]], str]:
    if category == "other":
        return [], "akshare_open_fund_rank"

    cached = session.exec(
        select(FundRankCache)
        .where(FundRankCache.category == category)
        .order_by(FundRankCache.fetched_at.desc())
    ).first()

    if _cache_is_fresh(cached):
        payload = json.loads(cached.payload_json)
        source = "akshare_money_rank" if category == MONEY_CATEGORY else "akshare_open_fund_rank"
        return payload, source

    if category == MONEY_CATEGORY:
        rows = _fetch_money_fund_rankings()
        source = "akshare_money_rank"
    else:
        rows = _fetch_open_fund_rankings()
        source = "akshare_open_fund_rank"

    session.exec(delete(FundRankCache).where(FundRankCache.category == category))
    session.add(
        FundRankCache(
            category=category,
            payload_json=json.dumps(rows, ensure_ascii=False),
            fetched_at=datetime.utcnow(),
        )
    )
    session.commit()
    return rows, source


def load_rank_fixture(session: Session, category: str, fixture_name: str) -> list[dict[str, Any]]:
    rows = _load_fixture(fixture_name)
    session.exec(delete(FundRankCache).where(FundRankCache.category == category))
    session.add(
        FundRankCache(
            category=category,
            payload_json=json.dumps(rows, ensure_ascii=False),
            fetched_at=datetime.utcnow(),
        )
    )
    session.commit()
    return rows


def _sort_key(field: str):
    def _key(item: dict[str, Any]) -> float:
        value = item.get(field)
        if value is None:
            return float("-inf")
        return float(value)

    return _key


def filter_rankings_for_category(
    session: Session,
    category: str,
    rows: list[dict[str, Any]],
    exclude_codes: set[str],
    limit: int = 3,
    sort_by: str = DEFAULT_SORT_FIELD,
) -> list[dict[str, Any]]:
    if category == MONEY_CATEGORY:
        candidates = rows
        sort_by = "return_1y"
    else:
        candidates = [
            row
            for row in rows
            if _matches_category(session, category, row["fund_code"], row["fund_name"])
        ]

    filtered: list[dict[str, Any]] = []
    for row in candidates:
        if row["fund_code"] in exclude_codes:
            continue
        filtered.append(row)

    filtered.sort(key=_sort_key(sort_by), reverse=True)
    return filtered[:limit]


def filter_rankings_for_theme(
    session: Session,
    theme_id: str,
    rows: list[dict[str, Any]],
    exclude_codes: set[str],
    limit: int = 3,
    sort_by: str = DEFAULT_SORT_FIELD,
) -> list[dict[str, Any]]:
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if row["fund_code"] in exclude_codes:
            continue
        entry = get_catalog_entry(session, row["fund_code"])
        fund_type = entry.fund_type if entry else ""
        name = entry.name if entry else row["fund_name"]
        if fund_matches_theme(name, fund_type, theme_id):
            filtered.append(row)

    filtered.sort(key=_sort_key(sort_by), reverse=True)
    return filtered[:limit]


def fetch_all_open_rankings(session: Session) -> tuple[list[dict[str, Any]], str]:
    cached = session.exec(
        select(FundRankCache)
        .where(FundRankCache.category == "all_open")
        .order_by(FundRankCache.fetched_at.desc())
    ).first()

    if _cache_is_fresh(cached):
        return json.loads(cached.payload_json), "akshare_open_fund_rank"

    rows = _fetch_open_fund_rankings()
    session.exec(delete(FundRankCache).where(FundRankCache.category == "all_open"))
    session.add(
        FundRankCache(
            category="all_open",
            payload_json=json.dumps(rows, ensure_ascii=False),
            fetched_at=datetime.utcnow(),
        )
    )
    session.commit()
    return rows, "akshare_open_fund_rank"
