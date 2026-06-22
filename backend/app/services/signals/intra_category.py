from __future__ import annotations

PERFORMANCE_BLOCK_RULES = frozenset(
    {"excess_return_1y", "peer_return_percentile_3m", "max_drawdown_1y", "sharpe_1y"}
)


def is_performance_blocked_add(perf_signal: dict | None) -> bool:
    if not perf_signal:
        return False
    if perf_signal.get("signal_type") == "reduce":
        return True
    if perf_signal.get("signal_type") != "watch":
        return False
    return any(
        reason.get("rule") in PERFORMANCE_BLOCK_RULES
        for reason in perf_signal.get("reasons") or []
        if reason.get("layer") == "performance"
    )


def performance_reduce_multiplier(perf_signal: dict | None) -> float:
    """Weak performers receive more of category reduce allocation."""
    if not perf_signal:
        return 1.0
    if perf_signal.get("signal_type") == "reduce":
        return 2.5
    if perf_signal.get("signal_type") == "watch":
        if any(
            reason.get("layer") == "performance"
            for reason in perf_signal.get("reasons") or []
        ):
            return 1.5
    return 1.0


def weight_surpluses_for_reduce(
    fund_surpluses: dict[str, float],
    perf_by_fund: dict[str, dict],
) -> dict[str, float]:
    weighted: dict[str, float] = {}
    for code, surplus in fund_surpluses.items():
        if surplus <= 0:
            weighted[code] = 0.0
            continue
        weighted[code] = round(surplus * performance_reduce_multiplier(perf_by_fund.get(code)), 2)
    return weighted


def resolve_intra_category_weights(
    mode: str,
    fund_categories: dict[str, str],
    market_value_by_code: dict[str, float],
    *,
    category: str,
    custom_weights: dict[str, float] | None,
) -> dict[str, float]:
    codes = [code for code, cat in fund_categories.items() if cat == category]
    if not codes:
        return {}

    if mode == "custom" and custom_weights:
        specified = {code: custom_weights[code] for code in codes if code in custom_weights}
        unspecified = [code for code in codes if code not in custom_weights]
        if not unspecified:
            total = sum(specified.values())
            return {code: value / total for code, value in specified.items()} if total else {}
        remaining = max(0.0, 1.0 - sum(specified.values()))
        share = remaining / len(unspecified) if unspecified else 0.0
        result = dict(specified)
        for code in unspecified:
            result[code] = share
        total = sum(result.values())
        return {code: value / total for code, value in result.items()} if total else {}

    if mode == "pro_rata":
        total_mv = sum(market_value_by_code.get(code, 0.0) for code in codes)
        if total_mv <= 0:
            count = len(codes)
            return {code: 1.0 / count for code in codes}
        return {code: market_value_by_code.get(code, 0.0) / total_mv for code in codes}

    count = len(codes)
    return {code: 1.0 / count for code in codes}


def compute_fund_gaps(
    *,
    market_value_by_code: dict[str, float],
    intra_weights: dict[str, float],
    total_value: float,
    category_target: float,
) -> dict[str, float]:
    gaps: dict[str, float] = {}
    for code, weight in intra_weights.items():
        target_mv = category_target * weight * total_value
        gap = target_mv - market_value_by_code.get(code, 0.0)
        gaps[code] = max(0.0, round(gap, 2))
    return gaps


def compute_fund_surpluses(
    *,
    market_value_by_code: dict[str, float],
    intra_weights: dict[str, float],
    total_value: float,
    category_target: float,
) -> dict[str, float]:
    surpluses: dict[str, float] = {}
    for code, weight in intra_weights.items():
        target_mv = category_target * weight * total_value
        surplus = market_value_by_code.get(code, 0.0) - target_mv
        surpluses[code] = max(0.0, round(surplus, 2))
    return surpluses


def allocate_category_add(
    *,
    category_gap_amount: float,
    fund_gaps: dict[str, float],
) -> dict[str, float]:
    positive = {code: gap for code, gap in fund_gaps.items() if gap > 0}
    total_gap = sum(positive.values())
    if total_gap <= 0 or category_gap_amount <= 0:
        return {code: 0.0 for code in fund_gaps}

    codes = sorted(positive.keys())
    amounts: dict[str, float] = {}
    allocated = 0.0
    for index, code in enumerate(codes):
        if index == len(codes) - 1:
            amounts[code] = round(category_gap_amount - allocated, 2)
        else:
            share = round(category_gap_amount * positive[code] / total_gap, 2)
            amounts[code] = share
            allocated += share
    for code in fund_gaps:
        amounts.setdefault(code, 0.0)
    return amounts


def allocate_category_reduce(
    *,
    category_reduce_amount: float,
    fund_surpluses: dict[str, float],
) -> dict[str, float]:
    positive = {code: surplus for code, surplus in fund_surpluses.items() if surplus > 0}
    total_surplus = sum(positive.values())
    if total_surplus <= 0 or category_reduce_amount <= 0:
        return {code: 0.0 for code in fund_surpluses}

    codes = sorted(positive.keys())
    amounts: dict[str, float] = {}
    allocated = 0.0
    for index, code in enumerate(codes):
        if index == len(codes) - 1:
            amounts[code] = round(-(category_reduce_amount - allocated), 2)
        else:
            share = round(category_reduce_amount * positive[code] / total_surplus, 2)
            amounts[code] = -share
            allocated += share
    for code in fund_surpluses:
        amounts.setdefault(code, 0.0)
    return amounts
