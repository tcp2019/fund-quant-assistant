from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime

from sqlmodel import Session, select

from app.db.models import Holding, PortfolioSnapshot, StrategyConfig
from app.repositories.portfolio import get_latest_snapshot
from app.schemas.settings import DEFAULT_TEMPLATES, DEFAULT_THRESHOLDS
from app.services.fund_classifier import classify_fund
from app.services.signals.rebalance import compute_rebalance_signals

SENSITIVITY_THRESHOLDS = (3.0, 5.0, 8.0, 10.0)


def _load_target_weights(session: Session) -> dict[str, float]:
    config = session.exec(select(StrategyConfig)).first()
    if config is None:
        return DEFAULT_TEMPLATES["balanced"]
    target = json.loads(config.target_weights_json) or DEFAULT_TEMPLATES["balanced"]
    return target


def _category_weights_from_holdings(
    session: Session,
    snapshot_id: int,
) -> tuple[dict[str, float], float]:
    holdings = session.exec(
        select(Holding).where(Holding.snapshot_id == snapshot_id)
    ).all()
    if not holdings:
        return {}, 0.0

    total_value = sum(holding.market_value for holding in holdings)
    if total_value <= 0:
        return {}, 0.0

    category_weights: dict[str, float] = defaultdict(float)
    for holding in holdings:
        category = classify_fund(holding.fund_name)
        category_weights[category] += holding.market_value / total_value
    return dict(category_weights), total_value


def build_sensitivity_report(session: Session) -> dict:
    snap = get_latest_snapshot(session)
    if snap is None:
        return {"snapshot_id": None, "total_value": 0.0, "scenarios": []}

    category_weights, total_value = _category_weights_from_holdings(session, snap.id)
    if not category_weights:
        return {"snapshot_id": snap.id, "total_value": 0.0, "scenarios": []}

    target = _load_target_weights(session)
    scenarios: list[dict] = []
    for threshold in SENSITIVITY_THRESHOLDS:
        signals = compute_rebalance_signals(
            category_weights, target, total_value, threshold_pct=threshold
        )
        triggered = [signal for signal in signals if signal["signal_type"] != "hold"]
        scenarios.append(
            {
                "threshold_pct": threshold,
                "triggered_categories": len(triggered),
                "signals": [
                    {
                        "category": signal["category"],
                        "signal_type": signal["signal_type"],
                        "deviation_pct": signal["deviation_pct"],
                        "suggested_amount": signal["suggested_amount"],
                    }
                    for signal in triggered
                ],
            }
        )

    return {
        "snapshot_id": snap.id,
        "total_value": round(total_value, 2),
        "scenarios": scenarios,
    }


def build_snapshot_stats(session: Session) -> dict:
    snapshots = session.exec(
        select(PortfolioSnapshot).order_by(PortfolioSnapshot.created_at.desc())
    ).all()
    target = _load_target_weights(session)
    config = session.exec(select(StrategyConfig)).first()
    thresholds = DEFAULT_THRESHOLDS
    if config and config.thresholds_json:
        thresholds = {**DEFAULT_THRESHOLDS, **json.loads(config.thresholds_json)}
    threshold = thresholds.get("rebalance_deviation_pct", 5.0)

    rows: list[dict] = []
    for snap in snapshots:
        category_weights, total_value = _category_weights_from_holdings(session, snap.id)
        if not category_weights or total_value <= 0:
            continue

        signals = compute_rebalance_signals(
            category_weights, target, total_value, threshold_pct=threshold
        )
        triggers = sum(1 for signal in signals if signal["signal_type"] != "hold")
        counts = defaultdict(int)
        holdings = session.exec(
            select(Holding).where(Holding.snapshot_id == snap.id)
        ).all()
        for holding in holdings:
            cat = classify_fund(holding.fund_name)
            counts[cat] += 1

        rows.append(
            {
                "snapshot_id": snap.id,
                "created_at": snap.created_at.isoformat()
                if isinstance(snap.created_at, datetime)
                else str(snap.created_at),
                "rebalance_triggers": triggers,
                "category_count_max": max(counts.values()) if counts else 0,
            }
        )

    return {"snapshots": rows}
