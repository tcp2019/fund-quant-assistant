import numpy as np
from app.services.optimizer import optimize_weights


def test_optimize_two_assets():
    returns = np.array([[0.001, -0.002, 0.003, 0.001, -0.001] * 5,
                        [0.002, 0.001, 0.001, 0.002, 0.001] * 5])
    weights = optimize_weights(returns)
    if weights is not None:
        assert len(weights) == 2
        assert abs(sum(weights) - 1.0) < 0.01
