"""Additional performance quality indicators for signal engine."""
from __future__ import annotations

import numpy as np

from app.services.metrics import daily_returns_from_navs, max_drawdown


def rolling_sharpe(returns: np.ndarray, window: int = 60) -> float:
    """Average of rolling-window Sharpe ratios. Returns 0 if insufficient data."""
    if len(returns) < window:
        return 0.0
    annual_factor = np.sqrt(252)
    sharpe_values = []
    for i in range(window, len(returns) + 1):
        window_rets = returns[i - window : i]
        std = window_rets.std(ddof=1)
        if std == 0:
            continue
        sharpe_values.append(window_rets.mean() / std * annual_factor)
    return float(np.mean(sharpe_values)) if sharpe_values else 0.0


def calmar_ratio(nav_series: list[float]) -> float:
    """Annualized return / max drawdown. Higher is better."""
    if len(nav_series) < 2:
        return 0.0
    navs = np.asarray(nav_series, dtype=float)
    returns = navs[1:] / navs[:-1] - 1
    annual_return = float(returns.mean() * 252)
    dd = max_drawdown(returns)
    if dd == 0 or dd >= 0:
        return 0.0
    return annual_return / abs(dd)


def downside_capture(
    fund_returns: np.ndarray,
    benchmark_returns: np.ndarray,
) -> float:
    """Ratio of fund's downside returns to benchmark's downside returns.
    > 100% means fund falls more than benchmark in down months."""
    if len(fund_returns) < 2 or len(benchmark_returns) < 2:
        return 100.0
    min_len = min(len(fund_returns), len(benchmark_returns))
    fund = fund_returns[-min_len:]
    bench = benchmark_returns[-min_len:]
    down_mask = bench < 0
    if not down_mask.any():
        return 100.0
    fund_down = fund[down_mask].mean()
    bench_down = bench[down_mask].mean()
    if bench_down == 0:
        return 100.0
    return float((fund_down / bench_down) * 100)


def info_ratio(
    fund_returns: np.ndarray,
    benchmark_returns: np.ndarray,
) -> float:
    """Annualized excess return over benchmark / tracking error."""
    if len(fund_returns) < 2 or len(benchmark_returns) < 2:
        return 0.0
    min_len = min(len(fund_returns), len(benchmark_returns))
    fund = fund_returns[-min_len:]
    bench = benchmark_returns[-min_len:]
    excess = fund - bench
    std = excess.std(ddof=1)
    if std == 0:
        return 0.0
    return float(excess.mean() / std * np.sqrt(252))
