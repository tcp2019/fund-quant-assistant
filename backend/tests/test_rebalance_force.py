from app.schemas.settings import DEFAULT_TEMPLATES
from app.services.signals.rebalance import compute_rebalance_signals


def test_force_review_no_longer_triggers_trades():
    category_weights = {
        "stock": 0.42,
        "bond": 0.28,
        "money": 0.15,
        "qdii": 0.10,
        "other": 0.05,
    }
    target = DEFAULT_TEMPLATES["balanced"]
    normal = compute_rebalance_signals(
        category_weights, target, total_value=10000, threshold_pct=5.0, force_review=False
    )
    forced = compute_rebalance_signals(
        category_weights, target, total_value=10000, threshold_pct=5.0, force_review=True
    )
    normal_bond = next(s for s in normal if s["category"] == "bond")
    forced_bond = next(s for s in forced if s["category"] == "bond")
    assert normal_bond["signal_type"] == "hold"
    assert forced_bond["signal_type"] == "hold"
