from app.services.signals.intra_category import (
    performance_reduce_multiplier,
    weight_surpluses_for_reduce,
)


def test_performance_reduce_multiplier_reduce_signal():
    assert performance_reduce_multiplier({"signal_type": "reduce", "reasons": []}) == 2.5


def test_performance_reduce_multiplier_watch_performance():
    assert (
        performance_reduce_multiplier(
            {
                "signal_type": "watch",
                "reasons": [{"layer": "performance", "rule": "sharpe_1y", "detail": "x"}],
            }
        )
        == 1.5
    )


def test_weight_surpluses_boosts_weak_performer():
    surpluses = {"A": 1000.0, "B": 1000.0}
    perf = {
        "A": {"signal_type": "reduce", "reasons": []},
        "B": {"signal_type": "hold", "reasons": []},
    }
    weighted = weight_surpluses_for_reduce(surpluses, perf)
    assert weighted["A"] > weighted["B"]
