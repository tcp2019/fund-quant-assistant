from app.schemas.settings import DEFAULT_TEMPLATES
from app.services.signals.rebalance import compute_rebalance_signals


def test_rebalance_underweight_bond():
    category_weights = {
        "stock": 0.50,
        "bond": 0.20,
        "money": 0.15,
        "qdii": 0.10,
        "other": 0.05,
    }
    target = DEFAULT_TEMPLATES["balanced"]
    signals = compute_rebalance_signals(
        category_weights, target, total_value=10000, threshold_pct=5.0
    )
    bond_signal = next(s for s in signals if s["category"] == "bond")
    assert bond_signal["signal_type"] == "add"
    assert bond_signal["deviation_pct"] == 10.0
    assert bond_signal["suggested_amount"] == 1000.0
