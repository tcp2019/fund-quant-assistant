from app.services.signals.consolidation import compute_consolidation_signals


def test_consolidation_triggers_when_too_many_funds():
    categories = {f"F{i}": "stock" for i in range(12)}
    signals = compute_consolidation_signals(
        categories,
        max_funds_per_category=10,
    )
    assert len(signals) == 1
    assert signals[0]["category"] == "stock"
    assert signals[0]["signal_type"] == "watch"


def test_consolidation_skips_small_categories():
    categories = {"A": "stock", "B": "bond"}
    signals = compute_consolidation_signals(
        categories,
        max_funds_per_category=10,
    )
    assert signals == []
