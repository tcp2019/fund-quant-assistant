import numpy as np
from app.services.signals.performance_metrics import (
    calmar_ratio,
    downside_capture,
    info_ratio,
    rolling_sharpe,
)


def test_rolling_sharpe_positive():
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.01, 120)
    rs = rolling_sharpe(returns, window=60)
    assert rs > 0


def test_rolling_sharpe_insufficient_data():
    returns = np.array([0.01, 0.02])
    rs = rolling_sharpe(returns, window=60)
    assert rs == 0.0


def test_calmar_ratio():
    navs = [1.0, 1.01, 1.02, 1.015, 1.03, 1.04]
    calmar = calmar_ratio(navs)
    assert calmar > 0


def test_calmar_ratio_negative():
    navs = [1.0, 0.95, 0.93, 0.90, 0.88, 0.85]
    calmar = calmar_ratio(navs)
    assert calmar < 0


def test_downside_capture():
    fund_rets = np.array([0.01, -0.02, 0.01, -0.03, 0.02, -0.01])
    bench_rets = np.array([0.005, -0.01, 0.005, -0.02, 0.01, -0.005])
    dc = downside_capture(fund_rets, bench_rets)
    assert dc > 100.0


def test_info_ratio():
    fund_rets = np.array([0.02, 0.01, 0.015, 0.005, 0.02])
    bench_rets = np.array([0.01, 0.01, 0.01, 0.01, 0.01])
    ir = info_ratio(fund_rets, bench_rets)
    assert ir > 0
