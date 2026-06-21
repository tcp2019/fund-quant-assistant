import numpy as np


def max_drawdown(returns: np.ndarray) -> float:
    cumulative = np.cumprod(1 + returns)
    peak = np.maximum.accumulate(cumulative)
    dd = cumulative / peak - 1
    return float(dd.min())


def sharpe_ratio(returns: np.ndarray, risk_free: float = 0.0, periods: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    excess = returns - risk_free / periods
    std = excess.std(ddof=1)
    if std == 0:
        return 0.0
    return float(excess.mean() / std * np.sqrt(periods))


def correlation_matrix(series_list: list[np.ndarray]) -> np.ndarray:
    if not series_list:
        return np.array([[]])
    mat = np.column_stack(series_list)
    corr = np.corrcoef(mat, rowvar=False)
    np.fill_diagonal(corr, 1.0)
    return corr


def daily_returns_from_navs(nav_series: list[float]) -> np.ndarray:
    if len(nav_series) < 2:
        return np.array([])
    navs = np.asarray(nav_series, dtype=float)
    return navs[1:] / navs[:-1] - 1
