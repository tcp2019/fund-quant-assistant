EXCESS_RETURN_THRESHOLD = -0.05
EXCESS_RETURN_REDUCE_THRESHOLD = -0.10
MAX_DRAWDOWN_BAD_THRESHOLD = -0.20  # placeholder for peer 75th percentile
SHARPE_MEDIAN_PLACEHOLDER = 0.8  # placeholder for peer median


def compute_performance_signals(
    fund_codes: list[str],
    metrics_by_code: dict[str, dict],
) -> list[dict]:
    signals: list[dict] = []

    for code in fund_codes:
        metrics = metrics_by_code.get(code, {})
        reasons: list[dict] = []

        excess = metrics.get("excess_return_1y")
        if excess is not None and excess < EXCESS_RETURN_THRESHOLD:
            pct = abs(excess) * 100
            reasons.append(
                {
                    "layer": "performance",
                    "rule": "excess_return_1y",
                    "detail": (
                        f"近1年超额收益 -{pct:.1f}%，"
                        f"低于基准 {abs(EXCESS_RETURN_THRESHOLD) * 100:.0f}%"
                    ),
                }
            )

        max_dd = metrics.get("max_drawdown_1y")
        if max_dd is not None and max_dd < MAX_DRAWDOWN_BAD_THRESHOLD:
            pct = abs(max_dd) * 100
            reasons.append(
                {
                    "layer": "performance",
                    "rule": "max_drawdown_1y",
                    "detail": f"最大回撤 {pct:.1f}%，超过同类75分位（placeholder）",
                }
            )

        sharpe = metrics.get("sharpe_1y")
        if sharpe is not None and sharpe < SHARPE_MEDIAN_PLACEHOLDER:
            reasons.append(
                {
                    "layer": "performance",
                    "rule": "sharpe_1y",
                    "detail": (
                        f"夏普比率 {sharpe:.2f}，"
                        f"低于同类中位数（placeholder {SHARPE_MEDIAN_PLACEHOLDER}）"
                    ),
                }
            )

        if not reasons:
            signal_type = "hold"
            detail = "业绩质量正常"
        elif (
            len(reasons) >= 2
            or (excess is not None and excess < EXCESS_RETURN_REDUCE_THRESHOLD)
        ):
            signal_type = "reduce"
            detail = "；".join(r["detail"] for r in reasons)
        else:
            signal_type = "watch"
            detail = reasons[0]["detail"]

        signals.append(
            {
                "fund_code": code,
                "signal_type": signal_type,
                "reasons": reasons,
                "detail": detail,
            }
        )

    return signals
