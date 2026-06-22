CATEGORY_LABELS = {
    "stock": "股票型",
    "bond": "债券型",
    "money": "货币/理财",
    "qdii": "QDII/海外",
    "other": "其他",
}


def compute_rebalance_signals(
    category_weights: dict[str, float],
    target: dict[str, float],
    total_value: float,
    threshold_pct: float,
    *,
    force_review: bool = False,
) -> list[dict]:
    del force_review  # v1.6: force review uses compute_rebalance_review_signals instead
    effective_threshold = threshold_pct
    categories = set(category_weights) | set(target)
    signals: list[dict] = []

    for category in sorted(categories):
        current = category_weights.get(category, 0.0)
        target_weight = target.get(category, 0.0)
        deviation_pct = round((target_weight - current) * 100, 2)
        suggested_amount = round((target_weight - current) * total_value, 2)

        if deviation_pct > effective_threshold:
            signal_type = "add"
            label = CATEGORY_LABELS.get(category, category)
            detail = f"{label}低配 {deviation_pct:.1f}%，建议增配 ¥{abs(suggested_amount):.0f}"
        elif deviation_pct < -effective_threshold:
            signal_type = "reduce"
            label = CATEGORY_LABELS.get(category, category)
            detail = f"{label}超配 {abs(deviation_pct):.1f}%，建议减配 ¥{abs(suggested_amount):.0f}"
        else:
            signal_type = "hold"
            detail = "权重在目标范围内"

        signals.append(
            {
                "category": category,
                "signal_type": signal_type,
                "deviation_pct": deviation_pct,
                "suggested_amount": suggested_amount,
                "detail": detail,
            }
        )

    return signals


def compute_rebalance_review_signals(
    category_weights: dict[str, float],
    target: dict[str, float],
    total_value: float,
    threshold_pct: float,
    *,
    force_review: bool,
) -> list[dict]:
    del total_value
    if not force_review:
        return []
    categories = set(category_weights) | set(target)
    signals: list[dict] = []
    for category in sorted(categories):
        current = category_weights.get(category, 0.0)
        target_weight = target.get(category, 0.0)
        deviation_pct = round((target_weight - current) * 100, 2)
        if deviation_pct == 0 or abs(deviation_pct) > threshold_pct:
            continue
        label = CATEGORY_LABELS.get(category, category)
        signals.append(
            {
                "category": category,
                "signal_type": "watch",
                "rule": "rebalance_review_due",
                "deviation_pct": deviation_pct,
                "suggested_amount": 0.0,
                "detail": (
                    f"年度审视：{label}偏离 {abs(deviation_pct):.1f}%"
                    f"（在 {threshold_pct:.0f}% 带宽内），建议关注"
                ),
            }
        )
    return signals
