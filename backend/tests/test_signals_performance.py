from app.services.signals.performance import compute_performance_signals


def test_underperform_benchmark():
    metrics = {
        "110011": {
            "excess_return_1y": -0.08,
            "sharpe_1y": 0.5,
            "max_drawdown_1y": -0.25,
        }
    }
    signals = compute_performance_signals(["110011"], metrics)
    assert signals[0]["signal_type"] in ("watch", "reduce")


def test_peer_percentile_triggers_watch():
    metrics = {
        "110011": {
            "peer_return_percentile_3m": 20.0,
            "sharpe_1y": 1.0,
            "max_drawdown_1y": -0.05,
        }
    }
    signals = compute_performance_signals(["110011"], metrics)
    assert signals[0]["signal_type"] == "watch"
    assert any(r["rule"] == "peer_return_percentile_3m" for r in signals[0]["reasons"])
