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
) -> list[dict]:
    categories = set(category_weights) | set(target)
    signals: list[dict] = []

    for category in sorted(categories):
        current = category_weights.get(category, 0.0)
        target_weight = target.get(category, 0.0)
        deviation_pct = round((target_weight - current) * 100, 2)
        suggested_amount = round((target_weight - current) * total_value, 2)

        if deviation_pct > threshold_pct:
            signal_type = "add"
            label = CATEGORY_LABELS.get(category, category)
            detail = f"{label}低配 {deviation_pct:.1f}%，建议增配 ¥{abs(suggested_amount):.0f}"
        elif deviation_pct < -threshold_pct:
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
