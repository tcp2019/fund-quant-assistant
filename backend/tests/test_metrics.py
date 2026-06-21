import numpy as np

from app.services.metrics import correlation_matrix, max_drawdown, sharpe_ratio


def test_max_drawdown():
    returns = np.array([0.1, -0.05, -0.2, 0.15])
    assert round(max_drawdown(returns), 4) == round(-0.24, 4)


def test_sharpe_ratio():
    returns = np.array([0.01, 0.02, -0.01, 0.015, 0.005])
    s = sharpe_ratio(returns, risk_free=0.0)
    assert s > 0


def test_correlation_matrix():
    a = np.array([0.01, 0.02, -0.01, 0.03])
    b = np.array([0.015, 0.01, -0.005, 0.02])
    corr = correlation_matrix([a, b])
    assert corr.shape == (2, 2)
    assert corr[0, 0] == 1.0
