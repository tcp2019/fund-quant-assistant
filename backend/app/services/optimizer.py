"""Mean-variance portfolio optimizer using scipy."""

import numpy as np

logger = __import__("logging").getLogger(__name__)


def optimize_weights(returns_matrix: np.ndarray) -> np.ndarray | None:
    """Find minimum-variance weights given historical returns matrix.
    returns_matrix: shape (n_assets, n_periods) — each row is an asset's return series
    Returns: optimal weights array or None if optimization fails
    """
    try:
        from scipy.optimize import minimize
    except ImportError:
        logger.warning("scipy not available, skipping optimization")
        return None

    n = returns_matrix.shape[0]
    if n < 2 or returns_matrix.shape[1] < 10:
        return None

    cov = np.cov(returns_matrix)
    mean_rets = returns_matrix.mean(axis=1)

    def portfolio_variance(w):
        return float(w @ cov @ w)

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1}]
    bounds = [(0.0, 1.0) for _ in range(n)]
    x0 = np.ones(n) / n

    result = minimize(portfolio_variance, x0, method="SLSQP", bounds=bounds, constraints=constraints)

    if result.success:
        return result.x
    return None
