from app.services.signals.performance import compute_performance_signals


def test_low_rolling_sharpe_triggers_watch():
    metrics = {"110011": {"sharpe_1y": 0.3, "rolling_sharpe": 0.3}}
    signals = compute_performance_signals(["110011"], metrics)
    assert len(signals) == 1
    rules = [r["rule"] for r in signals[0]["reasons"]]
    assert "low_rolling_sharpe" in rules or "sharpe_1y" in rules


def test_all_new_rules_appear():
    metrics = {
        "110011": {
            "sharpe_1y": 0.2,
            "max_drawdown_1y": -0.35,
            "excess_return_1y": -0.12,
            "rolling_sharpe": 0.3,
            "calmar": 0.15,
            "downside_capture": 140.0,
            "info_ratio": -0.8,
        }
    }
    signals = compute_performance_signals(["110011"], metrics)
    rules = [r["rule"] for r in signals[0]["reasons"]]
    assert "low_rolling_sharpe" in rules
    assert "low_calmar" in rules
    assert "high_downside_capture" in rules
    assert "low_info_ratio" in rules
