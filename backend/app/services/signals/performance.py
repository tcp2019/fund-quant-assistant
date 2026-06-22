EXCESS_RETURN_THRESHOLD = -0.05
EXCESS_RETURN_REDUCE_THRESHOLD = -0.10
MAX_DRAWDOWN_BAD_THRESHOLD = -0.20
SHARPE_WEAK_THRESHOLD = 0.5
PEER_UNDERPERFORM_PERCENTILE = 25.0


def compute_performance_signals(
    fund_codes: list[str],
    metrics_by_code: dict[str, dict],
) -> list[dict]:
    signals: list[dict] = []

    for code in fund_codes:
        metrics = metrics_by_code.get(code, {})
        reasons: list[dict] = []

        excess = metrics.get("excess_return_1y")
        peer_percentile = metrics.get("peer_return_percentile_3m")
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
        elif peer_percentile is not None and peer_percentile < PEER_UNDERPERFORM_PERCENTILE:
            reasons.append(
                {
                    "layer": "performance",
                    "rule": "peer_return_percentile_3m",
                    "detail": (
                        f"近3月同类收益排名后 {100 - peer_percentile:.0f}%"
                        f"（百分位 {peer_percentile:.1f}%）"
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
                    "detail": f"最大回撤 {pct:.1f}%，风险偏高",
                }
            )

        sharpe = metrics.get("sharpe_1y")
        if sharpe is not None and sharpe < SHARPE_WEAK_THRESHOLD:
            reasons.append(
                {
                    "layer": "performance",
                    "rule": "sharpe_1y",
                    "detail": f"夏普比率 {sharpe:.2f}，低于 {SHARPE_WEAK_THRESHOLD}",
                }
            )

        if not reasons:
            signal_type = "hold"
            detail = "业绩质量正常"
        elif (
            len(reasons) >= 2
            or (excess is not None and excess < EXCESS_RETURN_REDUCE_THRESHOLD)
            or (
                peer_percentile is not None
                and peer_percentile < PEER_UNDERPERFORM_PERCENTILE / 2
            )
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
