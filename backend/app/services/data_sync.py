import json
import logging
from typing import Any

import akshare as ak
from sqlmodel import Session, select

logger = logging.getLogger(__name__)

from app.db.models import FundMetadata, FundNavHistory, Holding, SyncLog
from app.repositories.portfolio import get_latest_snapshot
from app.services.fund_classifier import classify_fund
from app.services.fund_themes import detect_themes
from app.services.holdings_revalue import revalue_holdings
from app.services.http_retry import with_retry as _with_retry
from app.services.metrics_cache import compute_and_cache_metrics
from app.services.peer_metrics import fetch_peer_return_percentile_3m, parse_user_themes

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


def fetch_purchase_limits_from_akshare() -> dict[str, dict[str, Any]]:
    def _fetch() -> dict[str, dict[str, Any]]:
        df = ak.fund_purchase_em()
        limits: dict[str, dict[str, Any]] = {}
        for _, row in df.iterrows():
            code = str(row.get("基金代码") or "").strip()
            if not code:
                continue
            raw_limit = row.get("日累计限定金额")
            min_amount = row.get("购买起点")
            limits[code] = {
                "purchase_status": str(row.get("申购状态") or ""),
                "purchase_min_amount": float(min_amount) if min_amount == min_amount else None,
                "daily_purchase_limit": float(raw_limit) if raw_limit == raw_limit else None,
            }
        return limits

    return _with_retry(_fetch)


def sync_purchase_limits(session: Session, codes: list[str]) -> int:
    if not codes:
        return 0

    limits_by_code = fetch_purchase_limits_from_akshare()
    updated = 0
    for code in codes:
        raw = limits_by_code.get(code)
        if raw is None:
            continue

        meta = session.get(FundMetadata, code)
        if meta is None:
            continue

        meta.purchase_status = raw["purchase_status"]
        meta.purchase_min_amount = raw["purchase_min_amount"]
        meta.daily_purchase_limit = raw["daily_purchase_limit"]
        updated += 1

    session.commit()
    return updated


NAV_DAILY_CHANGE_THRESHOLD = 0.15  # 日涨跌超过 15% 视为异常


def detect_nav_jump(navs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """检测净值跳变，返回异常日期列表（通常是分红/拆分未复权，或数据源异常）。"""
    if len(navs) < 2:
        return []

    sorted_navs = sorted(navs, key=lambda x: x["date"])
    anomalies: list[dict[str, Any]] = []

    for i in range(1, len(sorted_navs)):
        prev_nav = sorted_navs[i - 1]["nav"]
        curr_nav = sorted_navs[i]["nav"]
        if prev_nav <= 0:
            continue
        change = abs(curr_nav / prev_nav - 1)
        if change > NAV_DAILY_CHANGE_THRESHOLD:
            anomalies.append(
                {
                    "date": sorted_navs[i]["date"],
                    "prev_nav": prev_nav,
                    "curr_nav": curr_nav,
                    "change_pct": round(change * 100, 2),
                    "likely_reason": "可能是分红/拆分未复权，或数据源异常",
                }
            )

    return anomalies


def sync_fund_nav(session: Session, code: str) -> int:
    latest = session.exec(
        select(FundNavHistory.date)
        .where(FundNavHistory.code == code)
        .order_by(FundNavHistory.date.desc())
    ).first()

    rows = fetch_nav_from_akshare(code)

    if latest:
        rows = [row for row in rows if row["date"] > latest]

    jump_anomalies = detect_nav_jump(rows)
    if jump_anomalies:
        logger.warning(
            "NAV jump detected for %s: %d anomalies",
            code,
            len(jump_anomalies),
        )

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


def _apply_themes(meta: FundMetadata, name: str, fund_type: str) -> None:
    user_themes = parse_user_themes(meta.user_themes_json)
    themes = detect_themes(name, fund_type, user_themes)
    meta.themes_json = json.dumps(themes, ensure_ascii=False)


def _apply_peer_metrics(session: Session, code: str) -> None:
    from app.db.models import FundMetricsCache

    cache = session.exec(
        select(FundMetricsCache)
        .where(FundMetricsCache.code == code)
        .order_by(FundMetricsCache.as_of_date.desc())
    ).first()
    if cache is None:
        return

    peer_percentile = fetch_peer_return_percentile_3m(code)
    cache.peer_return_percentile_3m = peer_percentile
    if peer_percentile is not None and cache.return_1y is not None and cache.excess_return_1y is None:
        if peer_percentile < 50:
            gap = (50.0 - peer_percentile) / 100.0
            cache.excess_return_1y = round(-gap * abs(cache.return_1y), 4)
    session.add(cache)


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
        _apply_themes(existing, name, meta["fund_type"])
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
        _apply_themes(record, name, meta["fund_type"])
        session.add(record)
    session.commit()
    session.refresh(record)
    return record


def sync_portfolio_funds(session: Session) -> dict[str, Any]:
    from datetime import datetime

    snap = get_latest_snapshot(session)
    if not snap:
        return {"synced": 0, "codes": [], "details": []}

    holdings = session.exec(
        select(Holding).where(Holding.snapshot_id == snap.id)
    ).all()
    codes = sorted({h.fund_code for h in holdings})
    name_by_code = {h.fund_code: h.fund_name for h in holdings}

    sync_log = SyncLog(
        started_at=datetime.utcnow(),
        status="running",
        total_funds=len(codes),
        success_funds=0,
        failed_funds=0,
        errors_json="[]",
    )
    session.add(sync_log)
    session.commit()

    details: list[dict[str, Any]] = []
    synced = 0
    errors: list[dict[str, Any]] = []

    # Per-fund metadata sync
    for code in codes:
        try:
            sync_fund_metadata(session, code, fallback_name=name_by_code.get(code, ""))
        except Exception as exc:
            errors.append({"fund_code": code, "stage": "metadata", "error": str(exc)})
            details.append({"code": code, "status": "metadata_error", "error": str(exc)})

    # Purchase limits (batch)
    try:
        sync_purchase_limits(session, codes)
    except Exception as exc:
        errors.append({"fund_code": "*", "stage": "purchase_limits", "error": str(exc)})
        details.append({"code": "*", "status": "purchase_limits_error", "error": str(exc)})

    # Per-fund NAV sync + metrics
    for code in codes:
        try:
            nav_rows = sync_fund_nav(session, code)
            metrics = compute_and_cache_metrics(session, code)
            try:
                _apply_peer_metrics(session, code)
                session.commit()
            except Exception as exc:
                errors.append({"fund_code": code, "stage": "peer_metrics", "error": str(exc)})
                details.append({"code": code, "status": "peer_metrics_error", "error": str(exc)})
            details.append(
                {
                    "code": code,
                    "nav_rows": nav_rows,
                    "metrics_cached": metrics is not None,
                    "status": "ok",
                }
            )
            synced += 1
        except Exception as exc:
            errors.append({"fund_code": code, "stage": "nav", "error": str(exc)})
            details.append({"code": code, "status": "error", "error": str(exc)})

    revalue = revalue_holdings(session, snap.id)

    # Update SyncLog
    sync_log.finished_at = datetime.utcnow()
    sync_log.success_funds = synced
    sync_log.failed_funds = len(codes) - synced
    sync_log.errors_json = json.dumps(errors, ensure_ascii=False)
    if synced == len(codes) and len(errors) == 0:
        sync_log.status = "done"
    elif synced > 0:
        sync_log.status = "partial"
    else:
        sync_log.status = "failed"
    session.add(sync_log)
    session.commit()

    return {
        "synced": synced,
        "codes": codes,
        "details": details,
        "revalued": revalue["updated"],
        "as_of_date": revalue["as_of_date"],
        "sync_log_id": sync_log.id,
    }
