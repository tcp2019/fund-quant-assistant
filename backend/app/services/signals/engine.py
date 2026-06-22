import json
from collections import defaultdict
from datetime import datetime

from sqlmodel import Session, select

from app.db.models import FundMetadata, FundMetricsCache, Holding, SignalRecord, StrategyConfig
from app.repositories.portfolio import get_latest_snapshot
from app.schemas.settings import DEFAULT_TEMPLATES, DEFAULT_THRESHOLDS
from app.services.analysis import compute_correlation
from app.services.fund_classifier import classify_fund
from app.services.signals.concentration import compute_concentration_signals
from app.services.signals.consolidation import compute_consolidation_signals
from app.services.signals.min_trade import apply_min_trade_to_signals
from app.services.signals.performance import compute_performance_signals
from app.services.signals.rebalance import CATEGORY_LABELS, compute_rebalance_review_signals, compute_rebalance_signals
from app.services.fund_purchase_limits import apply_purchase_limits_to_signals, purchase_info_from_metadata
from app.services.signals.intra_category import (
    allocate_category_add,
    allocate_category_reduce,
    compute_fund_gaps,
    compute_fund_surpluses,
    is_performance_blocked_add,
    performance_reduce_multiplier,
    resolve_intra_category_weights,
    weight_surpluses_for_reduce,
)

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


def _rebalance_rule(signal_type: str) -> str:
    if signal_type == "add":
        return "category_underweight"
    if signal_type == "reduce":
        return "category_overweight"
    return signal_type


def _derive_fund_signal_type(
    score: float,
    reasons: list[dict],
    suggested_amount: float,
) -> str:
    signal_type = _score_to_signal_type(score)
    if signal_type != "hold":
        return signal_type

    rebalance_rules = {
        reason.get("rule")
        for reason in reasons
        if reason.get("layer") == "rebalance"
    }
    if (
        suggested_amount > 0
        and score > 0
        and rebalance_rules & {"add", "category_underweight"}
    ):
        return "add"
    if (
        suggested_amount < 0
        and score < 0
        and rebalance_rules & {"reduce", "category_overweight"}
    ):
        return "reduce"
    return "hold"


def _layer_contribution(signal_type: str, weight: float, intensity: float = 1.0) -> float:
    base = SIGNAL_TYPE_SCORE.get(signal_type, 0.0)
    clamped = max(0.0, min(intensity, 1.0))
    return base * weight * clamped


def _format_intra_category_detail(
    rebalance_signal: dict,
    allocated: float,
    intra_gap: float,
    category_target: float,
    intra_weight: float,
) -> str:
    base = rebalance_signal["detail"]
    if allocated <= 0:
        return f"{base}；类内未分配"
    target_pct = category_target * intra_weight * 100
    return (
        f"{base}；类内分配 ¥{allocated:.0f}"
        f"（类内缺口 ¥{intra_gap:.0f}，目标占比 {target_pct:.1f}%）"
    )


def _build_category_add_amounts(
    rebalance: list[dict],
    fund_categories: dict[str, str],
    market_value_by_code: dict[str, float],
    total_value: float,
    category_targets: dict[str, float],
    intra_category_mode: str,
    fund_target_weights: dict[str, float] | None,
    perf_by_fund: dict[str, dict],
    overcrowded_categories: set[str] | None = None,
) -> tuple[dict[str, float], dict[str, float], dict[str, float], set[str], set[str]]:
    amounts: dict[str, float] = defaultdict(float)
    gaps_by_code: dict[str, float] = {}
    weights_by_code: dict[str, float] = {}
    blocked: set[str] = set()
    consolidation_blocked: set[str] = set()
    overcrowded = overcrowded_categories or set()

    for signal in rebalance:
        if signal["signal_type"] != "add":
            continue
        category = signal["category"]
        gap_amount = abs(signal["suggested_amount"])
        category_target = category_targets.get(category, 0.0)
        intra_weights = resolve_intra_category_weights(
            intra_category_mode,
            fund_categories,
            market_value_by_code,
            category=category,
            custom_weights=fund_target_weights,
        )
        fund_gaps = compute_fund_gaps(
            market_value_by_code=market_value_by_code,
            intra_weights=intra_weights,
            total_value=total_value,
            category_target=category_target,
        )
        for code in intra_weights:
            weights_by_code[code] = intra_weights[code]
            if is_performance_blocked_add(perf_by_fund.get(code)):
                blocked.add(code)
                fund_gaps[code] = 0.0
            gaps_by_code[code] = fund_gaps.get(code, 0.0)
        allocated = allocate_category_add(
            category_gap_amount=gap_amount,
            fund_gaps=fund_gaps,
        )
        if category in overcrowded:
            for code in intra_weights:
                if fund_gaps.get(code, 0.0) > 0 or allocated.get(code, 0.0) > 0:
                    consolidation_blocked.add(code)
                    allocated[code] = 0.0
        for code, value in allocated.items():
            amounts[code] += value

    return dict(amounts), gaps_by_code, weights_by_code, blocked, consolidation_blocked


def _build_category_reduce_amounts(
    rebalance: list[dict],
    fund_categories: dict[str, str],
    market_value_by_code: dict[str, float],
    total_value: float,
    category_targets: dict[str, float],
    intra_category_mode: str,
    fund_target_weights: dict[str, float] | None,
    perf_by_fund: dict[str, dict],
) -> tuple[dict[str, float], dict[str, float], set[str]]:
    amounts: dict[str, float] = defaultdict(float)
    surpluses_by_code: dict[str, float] = {}
    performance_boosted: set[str] = set()

    for signal in rebalance:
        if signal["signal_type"] != "reduce":
            continue
        category = signal["category"]
        reduce_amount = abs(signal["suggested_amount"])
        category_target = category_targets.get(category, 0.0)
        intra_weights = resolve_intra_category_weights(
            intra_category_mode,
            fund_categories,
            market_value_by_code,
            category=category,
            custom_weights=fund_target_weights,
        )
        fund_surpluses = compute_fund_surpluses(
            market_value_by_code=market_value_by_code,
            intra_weights=intra_weights,
            total_value=total_value,
            category_target=category_target,
        )
        for code in intra_weights:
            surpluses_by_code[code] = fund_surpluses.get(code, 0.0)
            if (
                fund_surpluses.get(code, 0.0) > 0
                and performance_reduce_multiplier(perf_by_fund.get(code)) > 1.0
            ):
                performance_boosted.add(code)
        weighted_surpluses = weight_surpluses_for_reduce(fund_surpluses, perf_by_fund)
        allocated = allocate_category_reduce(
            category_reduce_amount=reduce_amount,
            fund_surpluses=weighted_surpluses,
        )
        for code, value in allocated.items():
            amounts[code] += value

    return dict(amounts), surpluses_by_code, performance_boosted


def aggregate_signals(
    rebalance: list[dict],
    concentration: list[dict],
    performance: list[dict],
    fund_categories: dict[str, str],
    *,
    market_value_by_code: dict[str, float] | None = None,
    total_value: float = 0.0,
    category_targets: dict[str, float] | None = None,
    intra_category_mode: str = "equal",
    fund_target_weights: dict[str, float] | None = None,
    overcrowded_categories: set[str] | None = None,
) -> list[dict]:
    market_value_by_code = market_value_by_code or {}
    category_targets = category_targets or {}
    rebalance_by_cat = {signal["category"]: signal for signal in rebalance}
    conc_by_fund: dict[str, list[dict]] = defaultdict(list)
    for signal in concentration:
        conc_by_fund[signal["fund_code"]].append(signal)
    perf_by_fund = {signal["fund_code"]: signal for signal in performance}

    add_amounts, gaps_by_code, weights_by_code, performance_blocked, consolidation_blocked = (
        _build_category_add_amounts(
        rebalance,
        fund_categories,
        market_value_by_code,
        total_value,
        category_targets,
        intra_category_mode,
        fund_target_weights,
        perf_by_fund,
        overcrowded_categories=overcrowded_categories,
    )
    )
    reduce_amounts, surpluses_by_code, performance_boosted_reduce = _build_category_reduce_amounts(
        rebalance,
        fund_categories,
        market_value_by_code,
        total_value,
        category_targets,
        intra_category_mode,
        fund_target_weights,
        perf_by_fund,
    )

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
            if rebalance_signal["signal_type"] == "add":
                suggested_amount += add_amounts.get(fund_code, 0.0)
                intra_weight = weights_by_code.get(fund_code, 0.0)
                intra_gap = gaps_by_code.get(fund_code, 0.0)
                detail = _format_intra_category_detail(
                    rebalance_signal,
                    suggested_amount,
                    intra_gap,
                    category_targets.get(category, 0.0),
                    intra_weight,
                )
            elif rebalance_signal["signal_type"] == "reduce":
                suggested_amount += reduce_amounts.get(fund_code, 0.0)
                intra_surplus = surpluses_by_code.get(fund_code, 0.0)
                detail = (
                    f"{rebalance_signal['detail']}；类内减配 ¥{abs(suggested_amount):.0f}"
                    f"（类内超配 ¥{intra_surplus:.0f}）"
                )
            else:
                detail = rebalance_signal["detail"]
            reasons.append(
                {
                    "layer": "rebalance",
                    "rule": _rebalance_rule(rebalance_signal["signal_type"]),
                    "detail": detail,
                }
            )
            if fund_code in performance_blocked:
                reasons.append(
                    {
                        "layer": "performance",
                        "rule": "performance_blocked_add",
                        "detail": "业绩偏弱，不参与增配分配",
                    }
                )
            if fund_code in consolidation_blocked:
                reasons.append(
                    {
                        "layer": "aggregate",
                        "rule": "consolidation_blocked_add",
                        "detail": "大类持仓过多，类内增配已暂停，建议先合并为核心持仓",
                    }
                )
            if fund_code in performance_boosted_reduce:
                reasons.append(
                    {
                        "layer": "performance",
                        "rule": "performance_prioritized_reduce",
                        "detail": "业绩偏弱，减配分配权重提高",
                    }
                )

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
        if fund_code in performance_blocked and suggested_amount > 0:
            score = min(score, 15.0)
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
                "signal_type": _derive_fund_signal_type(score, reasons, suggested_amount),
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

    for rebalance_signal in rebalance:
        if rebalance_signal["signal_type"] != "reduce":
            continue
        intensity = min(abs(rebalance_signal["deviation_pct"]) / 20.0, 1.0)
        category_score = round(
            _layer_contribution("reduce", LAYER_WEIGHTS["rebalance"], intensity), 2
        )
        label = CATEGORY_LABELS.get(rebalance_signal["category"], rebalance_signal["category"])
        results.append(
            {
                "fund_code": "",
                "category": rebalance_signal["category"],
                "signal_type": "reduce",
                "score": category_score,
                "strength": _score_to_strength(category_score),
                "reasons": [
                    {
                        "layer": "rebalance",
                        "rule": "category_overweight",
                        "detail": rebalance_signal["detail"],
                        "category": rebalance_signal["category"],
                        "category_label": label,
                    }
                ],
                "suggested_amount": rebalance_signal["suggested_amount"],
                "category_label": label,
            }
        )

    return results


def append_review_signals(
    results: list[dict],
    review: list[dict],
) -> list[dict]:
    for signal in review:
        label = CATEGORY_LABELS.get(signal["category"], signal["category"])
        score = round(_layer_contribution("watch", LAYER_WEIGHTS["rebalance"], 0.5), 2)
        results.append(
            {
                "fund_code": "",
                "category": signal["category"],
                "signal_type": "watch",
                "score": score,
                "strength": _score_to_strength(score),
                "reasons": [
                    {
                        "layer": "rebalance",
                        "rule": "rebalance_review_due",
                        "detail": signal["detail"],
                        "category": signal["category"],
                        "category_label": label,
                    }
                ],
                "suggested_amount": 0.0,
                "category_label": label,
            }
        )
    return results


def append_consolidation_signals(
    results: list[dict],
    consolidation: list[dict],
) -> list[dict]:
    for signal in consolidation:
        label = CATEGORY_LABELS.get(signal["category"], signal["category"])
        score = round(_layer_contribution("watch", LAYER_WEIGHTS["concentration"], 1.0), 2)
        results.append(
            {
                "fund_code": "",
                "category": signal["category"],
                "signal_type": "watch",
                "score": score,
                "strength": _score_to_strength(score),
                "reasons": [
                    {
                        "layer": "concentration",
                        "rule": "category_overcrowded",
                        "detail": signal["detail"],
                        "category": signal["category"],
                        "category_label": label,
                    }
                ],
                "suggested_amount": 0.0,
                "category_label": label,
            }
        )
    return results


def _load_strategy(session: Session) -> tuple[dict[str, float], dict, str, dict[str, float]]:
    config = session.exec(select(StrategyConfig)).first()
    if config:
        target = json.loads(config.target_weights_json) or DEFAULT_TEMPLATES["balanced"]
        thresholds = json.loads(config.thresholds_json) or DEFAULT_THRESHOLDS
        mode = config.intra_category_mode or "equal"
        fund_targets = json.loads(config.fund_target_weights_json or "{}")
        if not isinstance(fund_targets, dict):
            fund_targets = {}
        return target, thresholds, mode, fund_targets
    return DEFAULT_TEMPLATES["balanced"], DEFAULT_THRESHOLDS, "equal", {}


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
            "peer_return_percentile_3m": cache.peer_return_percentile_3m,
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
    market_value_by_code: dict[str, float] = {}
    holdings_payload: list[dict] = []

    for holding in holdings:
        meta = session.get(FundMetadata, holding.fund_code)
        category = meta.category if meta else classify_fund(holding.fund_name)
        fund_categories[holding.fund_code] = category
        market_value_by_code[holding.fund_code] = holding.market_value
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

    target, thresholds, intra_category_mode, fund_target_weights = _load_strategy(session)
    days_since_snapshot = 0
    if snap.created_at is not None:
        created = snap.created_at
        if created.tzinfo is not None:
            created = created.replace(tzinfo=None)
        days_since_snapshot = (datetime.utcnow() - created).days
    force_review = days_since_snapshot >= thresholds.get("rebalance_force_days", 365)
    rebalance = compute_rebalance_signals(
        dict(category_weights),
        target,
        total_value,
        thresholds["rebalance_deviation_pct"],
        force_review=force_review,
    )
    review = compute_rebalance_review_signals(
        dict(category_weights),
        target,
        total_value,
        thresholds["rebalance_deviation_pct"],
        force_review=force_review,
    )
    corr_payload = compute_correlation(session)
    corr_matrix = (
        corr_payload
        if corr_payload.get("labels") and corr_payload.get("matrix")
        else None
    )
    concentration = compute_concentration_signals(
        holdings_payload,
        corr_matrix=corr_matrix,
        thresholds=thresholds,
    )
    consolidation = compute_consolidation_signals(
        fund_categories,
        max_funds_per_category=int(thresholds.get("max_funds_per_category", 10)),
        corr_matrix=corr_matrix,
        correlation_max=thresholds.get("correlation_max", 0.85),
    )
    overcrowded_categories = {signal["category"] for signal in consolidation}
    performance = compute_performance_signals(
        [holding.fund_code for holding in holdings],
        _load_metrics(session, [holding.fund_code for holding in holdings]),
        fund_categories=fund_categories,
    )

    aggregated = aggregate_signals(
        rebalance,
        concentration,
        performance,
        fund_categories,
        market_value_by_code=market_value_by_code,
        total_value=total_value,
        category_targets=target,
        intra_category_mode=intra_category_mode,
        fund_target_weights=fund_target_weights,
        overcrowded_categories=overcrowded_categories,
    )
    aggregated = append_consolidation_signals(aggregated, consolidation)
    aggregated = append_review_signals(aggregated, review)
    aggregated = apply_min_trade_to_signals(
        aggregated, thresholds.get("min_suggested_trade_cny", 500.0)
    )

    purchase_info_by_code = {
        code: purchase_info_from_metadata(session.get(FundMetadata, code))
        for code in fund_categories
    }
    purchase_info_by_code = {
        code: info for code, info in purchase_info_by_code.items() if info is not None
    }
    aggregated = apply_purchase_limits_to_signals(aggregated, purchase_info_by_code)

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
