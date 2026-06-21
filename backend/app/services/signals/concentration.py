REDEMPTION_FEE_MIN_HOLD_DAYS = 7


def compute_concentration_signals(
    holdings: list[dict],
    corr_matrix: dict | None,
    thresholds: dict,
) -> list[dict]:
    signals: list[dict] = []
    max_pct = thresholds["single_fund_max_pct"]
    corr_max = thresholds["correlation_max"]

    for holding in holdings:
        fund_code = holding["fund_code"]
        weight_pct = holding["weight_pct"]
        hold_days = holding.get("hold_days")

        if weight_pct <= max_pct:
            continue

        if hold_days is not None and hold_days < REDEMPTION_FEE_MIN_HOLD_DAYS:
            signals.append(
                {
                    "fund_code": fund_code,
                    "signal_type": "hold",
                    "weight_pct": weight_pct,
                    "detail": (
                        f"单只占比 {weight_pct:.1f}% 超过 {max_pct:.0f}%，"
                        f"但持有仅 {hold_days} 天，7 日内赎回费较高，暂不建议卖出"
                    ),
                }
            )
        else:
            signals.append(
                {
                    "fund_code": fund_code,
                    "signal_type": "reduce",
                    "weight_pct": weight_pct,
                    "detail": (
                        f"单只占比 {weight_pct:.1f}% 超过 {max_pct:.0f}%，建议减仓分散风险"
                    ),
                }
            )

    if corr_matrix is not None:
        labels = corr_matrix["labels"]
        matrix = corr_matrix["matrix"]
        n = len(labels)
        for i in range(n):
            for j in range(i + 1, n):
                corr = float(matrix[i][j])
                if corr > corr_max:
                    signals.append(
                        {
                            "fund_code": labels[i],
                            "paired_fund_code": labels[j],
                            "signal_type": "watch",
                            "correlation": round(corr, 4),
                            "detail": (
                                f"{labels[i]} 与 {labels[j]} 相关系数 "
                                f"{corr:.2f} 超过 {corr_max:.2f}，存在同源暴露，建议合并或减一只"
                            ),
                        }
                    )

    return signals
