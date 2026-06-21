import numpy as np

from app.schemas.settings import DEFAULT_THRESHOLDS
from app.services.signals.concentration import compute_concentration_signals


def test_single_fund_concentration():
    holdings = [{"fund_code": "110011", "weight_pct": 30.0, "hold_days": 30}]
    signals = compute_concentration_signals(
        holdings, corr_matrix=None, thresholds=DEFAULT_THRESHOLDS
    )
    assert signals[0]["signal_type"] == "reduce"
    assert "25%" in signals[0]["detail"]


def test_hold_days_blocks_sell():
    holdings = [{"fund_code": "110011", "weight_pct": 30.0, "hold_days": 3}]
    signals = compute_concentration_signals(
        holdings, corr_matrix=None, thresholds=DEFAULT_THRESHOLDS
    )
    assert signals[0]["signal_type"] == "hold"
    assert "7" in signals[0]["detail"]


def test_high_correlation_pair():
    holdings = [
        {"fund_code": "110011", "weight_pct": 15.0, "hold_days": 30},
        {"fund_code": "110022", "weight_pct": 15.0, "hold_days": 30},
    ]
    corr_matrix = {
        "labels": ["110011", "110022"],
        "matrix": np.array([[1.0, 0.92], [0.92, 1.0]]),
    }
    signals = compute_concentration_signals(
        holdings, corr_matrix=corr_matrix, thresholds=DEFAULT_THRESHOLDS
    )
    corr_signals = [s for s in signals if s["signal_type"] == "watch"]
    assert len(corr_signals) == 1
    assert corr_signals[0]["fund_code"] == "110011"
    assert corr_signals[0]["paired_fund_code"] == "110022"
    assert "0.85" in corr_signals[0]["detail"]
