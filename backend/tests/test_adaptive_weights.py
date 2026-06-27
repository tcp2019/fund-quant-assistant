from app.services.signals.adaptive_weights import get_adaptive_weights


def test_tight_weights():
    w = get_adaptive_weights("tight")
    assert w["concentration"] == 0.4
    assert w["performance"] == 0.2


def test_loose_weights():
    w = get_adaptive_weights("loose")
    assert w["rebalance"] == 0.5
    assert w["concentration"] == 0.2


def test_neutral_default():
    w = get_adaptive_weights("neutral")
    assert w == {"rebalance": 0.4, "concentration": 0.3, "performance": 0.3}


def test_unknown_default():
    w = get_adaptive_weights("garbage")
    assert w["rebalance"] == 0.4
