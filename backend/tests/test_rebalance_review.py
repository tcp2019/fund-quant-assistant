from app.schemas.settings import DEFAULT_TEMPLATES
from app.services.signals.engine import append_review_signals
from app.services.signals.rebalance import (
    compute_rebalance_review_signals,
    compute_rebalance_signals,
)


def test_force_review_does_not_change_rebalance_trades():
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
    assert normal == forced


def test_review_signals_within_band_only():
    category_weights = {
        "stock": 0.42,
        "bond": 0.28,
        "money": 0.15,
        "qdii": 0.10,
        "other": 0.05,
    }
    target = DEFAULT_TEMPLATES["balanced"]
    reviews = compute_rebalance_review_signals(
        category_weights, target, total_value=10000, threshold_pct=5.0, force_review=True
    )
    assert len(reviews) >= 1
    bond = next(s for s in reviews if s["category"] == "bond")
    assert bond["signal_type"] == "watch"
    assert bond["rule"] == "rebalance_review_due"
    assert bond["suggested_amount"] == 0.0


def test_review_skipped_when_force_review_false():
    category_weights = {"stock": 0.42, "bond": 0.28}
    target = DEFAULT_TEMPLATES["balanced"]
    assert (
        compute_rebalance_review_signals(
            category_weights, target, 10000, 5.0, force_review=False
        )
        == []
    )


def test_append_review_signals_adds_category_watch_rows():
    reviews = [
        {
            "category": "bond",
            "signal_type": "watch",
            "rule": "rebalance_review_due",
            "detail": "年度审视：债券型偏离 2.0%（在 5% 带宽内），建议关注",
            "suggested_amount": 0.0,
        }
    ]
    results = append_review_signals([], reviews)
    assert len(results) == 1
    assert results[0]["fund_code"] == ""
    assert results[0]["reasons"][0]["rule"] == "rebalance_review_due"
