import json
from datetime import datetime, timedelta

import akshare as ak
from sqlalchemy import func, or_
from sqlmodel import Session, delete, select

from app.db.models import FundCatalog
from app.services.fund_themes import theme_search_keywords

CATALOG_TTL_DAYS = 7


def _catalog_is_stale(session: Session) -> bool:
    latest = session.exec(select(func.max(FundCatalog.synced_at))).one()
    if latest is None:
        return True
    return datetime.utcnow() - latest > timedelta(days=CATALOG_TTL_DAYS)


def refresh_catalog(session: Session) -> int:
    df = ak.fund_name_em()
    synced_at = datetime.utcnow()
    session.exec(delete(FundCatalog))
    count = 0
    for _, row in df.iterrows():
        session.add(
            FundCatalog(
                code=str(row["基金代码"]).zfill(6),
                name=str(row["基金简称"]),
                fund_type=str(row.get("基金类型") or ""),
                pinyin_abbr=str(row.get("拼音缩写") or ""),
                synced_at=synced_at,
            )
        )
        count += 1
    session.commit()
    return count


def ensure_catalog(session: Session, force: bool = False) -> bool:
    total = session.exec(select(func.count()).select_from(FundCatalog)).one()
    if total == 0 or force or _catalog_is_stale(session):
        refresh_catalog(session)
        return True
    return False


def search_catalog(session: Session, query: str, limit: int = 8) -> list[FundCatalog]:
    q = query.strip()
    if not q:
        return []

    total = session.exec(select(func.count()).select_from(FundCatalog)).one()
    if total == 0:
        return []

    if q.isdigit():
        rows = session.exec(
            select(FundCatalog).where(FundCatalog.code.startswith(q)).limit(limit)
        ).all()
        if rows:
            return list(rows)

    theme_keywords = theme_search_keywords(q)
    if theme_keywords:
        clauses = [FundCatalog.name.contains(keyword) for keyword in theme_keywords]
        rows = session.exec(select(FundCatalog).where(or_(*clauses)).limit(limit)).all()
        if rows:
            return list(rows)

    rows = session.exec(
        select(FundCatalog)
        .where(or_(FundCatalog.name.contains(q), FundCatalog.code.contains(q)))
        .limit(limit)
    ).all()
    return list(rows)


def get_catalog_entry(session: Session, code: str) -> FundCatalog | None:
    return session.get(FundCatalog, code)


def load_catalog_fixture(session: Session, fixture_name: str = "fund_name_em_sample.json") -> int:
    from pathlib import Path

    path = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "akshare" / fixture_name
    rows = json.loads(path.read_text(encoding="utf-8"))
    synced_at = datetime.utcnow()
    session.exec(delete(FundCatalog))
    for row in rows:
        session.add(
            FundCatalog(
                code=str(row["基金代码"]).zfill(6),
                name=str(row["基金简称"]),
                fund_type=str(row.get("基金类型") or ""),
                pinyin_abbr=str(row.get("拼音缩写") or ""),
                synced_at=synced_at,
            )
        )
    session.commit()
    return len(rows)
