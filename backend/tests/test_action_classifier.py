from app.services.signals.action_classifier import classify_signal_action


def test_reduce_is_sell():
    assert classify_signal_action("reduce", [], -5000.0, -30.0) == "reduce"


def test_purchase_limit_maps_to_watch():
    reasons = [{"layer": "purchase_limit", "rule": "purchase_limit_blocked", "detail": "x"}]
    assert classify_signal_action("add", reasons, 1000.0, 20.0) == "watch"


def test_hold_with_rebalance_add_maps_to_add():
    reasons = [
        {"layer": "rebalance", "rule": "category_underweight", "detail": "低配"},
        {"layer": "rebalance", "rule": "add", "detail": "增配"},
    ]
    assert classify_signal_action("hold", reasons, 500.0, 18.0) == "add"


def test_hold_reduce_maps_to_reduce():
    reasons = [
        {"layer": "rebalance", "rule": "category_overweight", "detail": "超配"},
        {"layer": "rebalance", "rule": "reduce", "detail": "减配"},
    ]
    assert classify_signal_action("hold", reasons, -800.0, -22.0) == "reduce"


def test_performance_blocked_add_maps_to_watch():
    reasons = [
        {"layer": "rebalance", "rule": "category_underweight", "detail": "低配"},
        {"layer": "performance", "rule": "performance_blocked_add", "detail": "过滤"},
    ]
    assert classify_signal_action("add", reasons, 1000.0, 25.0) == "watch"


def test_consolidation_blocked_add_maps_to_watch():
    reasons = [
        {"layer": "rebalance", "rule": "category_underweight", "detail": "低配"},
        {"layer": "aggregate", "rule": "consolidation_blocked_add", "detail": "暂停"},
    ]
    assert classify_signal_action("add", reasons, 1000.0, 25.0) == "watch"
