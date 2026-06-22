EXCESS_RETURN_THRESHOLD = -0.05
EXCESS_RETURN_REDUCE_THRESHOLD = -0.10
PEER_UNDERPERFORM_PERCENTILE = 25.0

CATEGORY_THRESHOLDS: dict[str, dict[str, float]] = {
    "stock": {"sharpe_weak": 0.5, "max_drawdown_bad": -0.20},
    "bond": {"sharpe_weak": 0.3, "max_drawdown_bad": -0.10},
    "money": {"sharpe_weak": 0.0, "max_drawdown_bad": -0.01},
    "qdii": {"sharpe_weak": 0.4, "max_drawdown_bad": -0.25},
    "other": {"sharpe_weak": 0.5, "max_drawdown_bad": -0.20},
}


def _thresholds_for_category(category: str) -> dict[str, float]:
    return CATEGORY_THRESHOLDS.get(category, CATEGORY_THRESHOLDS["other"])


def compute_performance_signals(
    fund_codes: list[str],
    metrics_by_code: dict[str, dict],
    fund_categories: dict[str, str] | None = None,
) -> list[dict]:
    fund_categories = fund_categories or {}
    signals: list[dict] = []

    for code in fund_codes:
        metrics = metrics_by_code.get(code, {})
        category = fund_categories.get(code, "other")
        thresholds = _thresholds_for_category(category)
        sharpe_weak = thresholds["sharpe_weak"]
        max_dd_bad = thresholds["max_drawdown_bad"]
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
        if max_dd is not None and max_dd < max_dd_bad:
            pct = abs(max_dd) * 100
            reasons.append(
                {
                    "layer": "performance",
                    "rule": "max_drawdown_1y",
                    "detail": f"最大回撤 {pct:.1f}%，风险偏高（{category} 阈值 {abs(max_dd_bad) * 100:.0f}%）",
                }
            )

        sharpe = metrics.get("sharpe_1y")
        if sharpe is not None and sharpe < sharpe_weak:
            reasons.append(
                {
                    "layer": "performance",
                    "rule": "sharpe_1y",
                    "detail": f"夏普比率 {sharpe:.2f}，低于 {category} 阈值 {sharpe_weak}",
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
