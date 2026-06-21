import time
from collections.abc import Callable
from typing import Any, TypeVar

import akshare as ak
from sqlmodel import Session, select

from app.db.models import FundMetadata, FundNavHistory, Holding
from app.repositories.portfolio import get_latest_snapshot
from app.services.fund_classifier import classify_fund

T = TypeVar("T")


def _with_retry(fn: Callable[[], T], max_attempts: int = 3, base_delay: float = 1.0) -> T:
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                time.sleep(base_delay * (2**attempt))
    raise last_exc  # type: ignore[misc]


def fetch_nav_from_akshare(code: str) -> list[dict[str, Any]]:
    def _fetch() -> list[dict[str, Any]]:
        nav_df = ak.fund_open_fund_info_em(
            symbol=code, indicator="单位净值走势", period="成立来"
        )
        acc_df = ak.fund_open_fund_info_em(
            symbol=code, indicator="累计净值走势", period="成立来"
        )

        acc_by_date = {
            str(row["净值日期"]): float(row["累计净值"])
            for _, row in acc_df.iterrows()
        }

        rows: list[dict[str, Any]] = []
        for _, row in nav_df.iterrows():
            date = str(row["净值日期"])
            nav = float(row["单位净值"])
            rows.append(
                {
                    "date": date,
                    "nav": nav,
                    "acc_nav": acc_by_date.get(date, nav),
                }
            )
        return rows

    return _with_retry(_fetch)


def fetch_metadata_from_akshare(code: str) -> dict[str, str]:
    def _fetch() -> dict[str, str]:
        df = ak.fund_overview_em(symbol=code)
        row = df.iloc[0]
        name = str(row.get("基金简称") or row.get("基金全称") or "")
        return {
            "name": name,
            "fund_type": str(row.get("基金类型") or ""),
            "manager": str(row.get("基金经理人") or ""),
            "benchmark_code": str(row.get("业绩比较基准") or ""),
        }

    return _with_retry(_fetch)


def sync_fund_nav(session: Session, code: str) -> int:
    rows = fetch_nav_from_akshare(code)
    synced = 0
    for row in rows:
        existing = session.exec(
            select(FundNavHistory).where(
                FundNavHistory.code == code,
                FundNavHistory.date == row["date"],
            )
        ).first()
        if existing:
            existing.nav = row["nav"]
            existing.acc_nav = row["acc_nav"]
        else:
            session.add(
                FundNavHistory(
                    code=code,
                    date=row["date"],
                    nav=row["nav"],
                    acc_nav=row["acc_nav"],
                )
            )
        synced += 1
    session.commit()
    return synced


def sync_fund_metadata(
    session: Session, code: str, fallback_name: str = ""
) -> FundMetadata:
    meta = fetch_metadata_from_akshare(code)
    name = meta["name"] or fallback_name
    category = classify_fund(name, meta["fund_type"])

    existing = session.get(FundMetadata, code)
    if existing:
        existing.name = name
        existing.fund_type = meta["fund_type"]
        existing.category = category
        existing.benchmark_code = meta["benchmark_code"]
        existing.manager = meta["manager"]
        record = existing
    else:
        record = FundMetadata(
            code=code,
            name=name,
            fund_type=meta["fund_type"],
            category=category,
            benchmark_code=meta["benchmark_code"],
            manager=meta["manager"],
        )
        session.add(record)
    session.commit()
    session.refresh(record)
    return record


def sync_portfolio_funds(session: Session) -> dict[str, Any]:
    snap = get_latest_snapshot(session)
    if not snap:
        return {"synced": 0, "codes": [], "details": []}

    holdings = session.exec(
        select(Holding).where(Holding.snapshot_id == snap.id)
    ).all()
    codes = sorted({h.fund_code for h in holdings})
    name_by_code = {h.fund_code: h.fund_name for h in holdings}

    details: list[dict[str, Any]] = []
    synced = 0
    for code in codes:
        try:
            sync_fund_metadata(session, code, fallback_name=name_by_code.get(code, ""))
            nav_rows = sync_fund_nav(session, code)
            details.append({"code": code, "nav_rows": nav_rows, "status": "ok"})
            synced += 1
        except Exception as exc:
            details.append({"code": code, "status": "error", "error": str(exc)})

    return {"synced": synced, "codes": codes, "details": details}
