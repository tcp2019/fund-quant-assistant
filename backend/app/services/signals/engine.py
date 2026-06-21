import json
from collections import defaultdict

from sqlmodel import Session, select

from app.db.models import FundMetadata, FundMetricsCache, Holding, SignalRecord, StrategyConfig
from app.repositories.portfolio import get_latest_snapshot
from app.schemas.settings import DEFAULT_TEMPLATES, DEFAULT_THRESHOLDS
from app.services.fund_classifier import classify_fund
from app.services.signals.concentration import compute_concentration_signals
from app.services.signals.performance import compute_performance_signals
from app.services.signals.rebalance import CATEGORY_LABELS, compute_rebalance_signals

LAYER_WEIGHTS = {"rebalance": 0.4, "concentration": 0.3, "performance": 0.3}

SIGNAL_TYPE_SCORE = {"add": 100.0, "reduce": -100.0, "hold": 0.0, "watch": -25.0}


def _score_to_strength(score: float) -> int:
    magnitude = abs(score)
    if magnitude < 15:
        return 1
    if magnitude < 35:
        return 2
    if magnitude < 55:
        return 3
    if magnitude < 75:
        return 4
    return 5


def _score_to_signal_type(score: float) -> str:
    if score >= 20:
        return "add"
    if score <= -20:
        return "reduce"
    if score <= -5:
        return "watch"
    return "hold"


def _layer_contribution(signal_type: str, weight: float, intensity: float = 1.0) -> float:
    base = SIGNAL_TYPE_SCORE.get(signal_type, 0.0)
    clamped = max(0.0, min(intensity, 1.0))
    return base * weight * clamped


def aggregate_signals(
    rebalance: list[dict],
    concentration: list[dict],
    performance: list[dict],
    fund_categories: dict[str, str],
) -> list[dict]:
    rebalance_by_cat = {signal["category"]: signal for signal in rebalance}
    conc_by_fund: dict[str, list[dict]] = defaultdict(list)
    for signal in concentration:
        conc_by_fund[signal["fund_code"]].append(signal)
    perf_by_fund = {signal["fund_code"]: signal for signal in performance}

    funds_per_category: dict[str, int] = defaultdict(int)
    for category in fund_categories.values():
        funds_per_category[category] += 1

    results: list[dict] = []

    for fund_code in sorted(fund_categories):
        category = fund_categories[fund_code]
        reasons: list[dict] = []
        score = 0.0
        suggested_amount = 0.0

        rebalance_signal = rebalance_by_cat.get(category)
        if rebalance_signal and rebalance_signal["signal_type"] != "hold":
            intensity = min(abs(rebalance_signal["deviation_pct"]) / 20.0, 1.0)
            score += _layer_contribution(
                rebalance_signal["signal_type"],
                LAYER_WEIGHTS["rebalance"],
                intensity,
            )
            reasons.append(
                {
                    "layer": "rebalance",
                    "rule": rebalance_signal["signal_type"],
                    "detail": rebalance_signal["detail"],
                }
            )
            if rebalance_signal["signal_type"] == "add":
                share = funds_per_category.get(category, 1)
                suggested_amount += abs(rebalance_signal["suggested_amount"]) / share

        for conc_signal in conc_by_fund.get(fund_code, []):
            intensity = 1.0
            if conc_signal["signal_type"] == "reduce" and "weight_pct" in conc_signal:
                intensity = min((conc_signal["weight_pct"] - 25.0) / 25.0, 1.0)
            score += _layer_contribution(
                conc_signal["signal_type"],
                LAYER_WEIGHTS["concentration"],
                intensity,
            )
            rule = (
                "high_correlation"
                if "paired_fund_code" in conc_signal
                else "single_fund_concentration"
            )
            reasons.append(
                {
                    "layer": "concentration",
                    "rule": rule,
                    "detail": conc_signal["detail"],
                }
            )

        perf_signal = perf_by_fund.get(fund_code)
        if perf_signal and perf_signal["signal_type"] != "hold":
            intensity = min(max(len(perf_signal.get("reasons", [])), 1) / 3.0, 1.0)
            score += _layer_contribution(
                perf_signal["signal_type"],
                LAYER_WEIGHTS["performance"],
                intensity,
            )
            reasons.extend(perf_signal.get("reasons", []))

        score = max(-100.0, min(100.0, round(score, 2)))
        if not reasons:
            reasons.append(
                {
                    "layer": "aggregate",
                    "rule": "no_action",
                    "detail": "各层信号正常，无需调整",
                }
            )

        results.append(
            {
                "fund_code": fund_code,
                "signal_type": _score_to_signal_type(score),
                "score": score,
                "strength": _score_to_strength(score),
                "reasons": reasons,
                "suggested_amount": round(suggested_amount, 2),
            }
        )

    for rebalance_signal in rebalance:
        if rebalance_signal["signal_type"] != "add":
            continue
        intensity = min(abs(rebalance_signal["deviation_pct"]) / 20.0, 1.0)
        category_score = round(
            _layer_contribution("add", LAYER_WEIGHTS["rebalance"], intensity), 2
        )
        label = CATEGORY_LABELS.get(rebalance_signal["category"], rebalance_signal["category"])
        results.append(
            {
                "fund_code": "",
                "category": rebalance_signal["category"],
                "signal_type": "add",
                "score": category_score,
                "strength": _score_to_strength(category_score),
                "reasons": [
                    {
                        "layer": "rebalance",
                        "rule": "category_underweight",
                        "detail": rebalance_signal["detail"],
                        "category": rebalance_signal["category"],
                        "category_label": label,
                    }
                ],
                "suggested_amount": abs(rebalance_signal["suggested_amount"]),
                "category_label": label,
            }
        )

    return results


def _load_strategy(session: Session) -> tuple[dict[str, float], dict]:
    config = session.exec(select(StrategyConfig)).first()
    if config:
        target = json.loads(config.target_weights_json) or DEFAULT_TEMPLATES["balanced"]
        thresholds = json.loads(config.thresholds_json) or DEFAULT_THRESHOLDS
        return target, thresholds
    return DEFAULT_TEMPLATES["balanced"], DEFAULT_THRESHOLDS


def _load_metrics(session: Session, fund_codes: list[str]) -> dict[str, dict]:
    metrics_by_code: dict[str, dict] = {}
    for code in fund_codes:
        cache = session.exec(
            select(FundMetricsCache)
            .where(FundMetricsCache.code == code)
            .order_by(FundMetricsCache.as_of_date.desc())
        ).first()
        if cache is None:
            continue
        metrics_by_code[code] = {
            "excess_return_1y": cache.excess_return_1y,
            "sharpe_1y": cache.sharpe_1y,
            "max_drawdown_1y": cache.max_drawdown_1y,
        }
    return metrics_by_code


def run_signal_engine(session: Session) -> list[SignalRecord]:
    snap = get_latest_snapshot(session)
    if snap is None:
        return []

    holdings = list(
        session.exec(select(Holding).where(Holding.snapshot_id == snap.id)).all()
    )
    if not holdings:
        return []

    total_value = sum(holding.market_value for holding in holdings)
    fund_categories: dict[str, str] = {}
    holdings_payload: list[dict] = []

    for holding in holdings:
        meta = session.get(FundMetadata, holding.fund_code)
        category = meta.category if meta else classify_fund(holding.fund_name)
        fund_categories[holding.fund_code] = category
        weight_pct = (holding.market_value / total_value * 100) if total_value else 0.0
        holdings_payload.append(
            {
                "fund_code": holding.fund_code,
                "fund_name": holding.fund_name,
                "weight_pct": round(weight_pct, 2),
                "hold_days": holding.hold_days,
            }
        )

    category_weights: dict[str, float] = defaultdict(float)
    for holding in holdings:
        category = fund_categories[holding.fund_code]
        share = holding.market_value / total_value if total_value else 0.0
        category_weights[category] += share

    target, thresholds = _load_strategy(session)
    rebalance = compute_rebalance_signals(
        dict(category_weights),
        target,
        total_value,
        thresholds["rebalance_deviation_pct"],
    )
    concentration = compute_concentration_signals(
        holdings_payload,
        corr_matrix=None,
        thresholds=thresholds,
    )
    performance = compute_performance_signals(
        [holding.fund_code for holding in holdings],
        _load_metrics(session, [holding.fund_code for holding in holdings]),
    )

    aggregated = aggregate_signals(
        rebalance,
        concentration,
        performance,
        fund_categories,
    )

    existing = session.exec(
        select(SignalRecord).where(SignalRecord.snapshot_id == snap.id)
    ).all()
    for record in existing:
        session.delete(record)

    records: list[SignalRecord] = []
    for signal in aggregated:
        record = SignalRecord(
            snapshot_id=snap.id,
            fund_code=signal.get("fund_code", ""),
            signal_type=signal["signal_type"],
            score=signal["score"],
            strength=signal["strength"],
            reasons_json=json.dumps(signal["reasons"], ensure_ascii=False),
            suggested_amount=signal.get("suggested_amount", 0.0),
        )
        session.add(record)
        records.append(record)

    session.commit()
    for record in records:
        session.refresh(record)
    return records
