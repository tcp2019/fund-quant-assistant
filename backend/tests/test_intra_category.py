from app.services.signals.intra_category import (
    allocate_category_add,
    compute_fund_gaps,
    is_performance_blocked_add,
    resolve_intra_category_weights,
)


def test_resolve_equal_weights():
    weights = resolve_intra_category_weights(
        "equal",
        {"A": "stock", "B": "stock", "C": "bond"},
        {"A": 1000.0, "B": 2000.0, "C": 500.0},
        category="stock",
        custom_weights=None,
    )
    assert weights == {"A": 0.5, "B": 0.5}


def test_resolve_pro_rata_weights():
    weights = resolve_intra_category_weights(
        "pro_rata",
        {"A": "stock", "B": "stock"},
        {"A": 1000.0, "B": 3000.0},
        category="stock",
        custom_weights=None,
    )
    assert abs(weights["A"] - 0.25) < 1e-9
    assert abs(weights["B"] - 0.75) < 1e-9


def test_compute_fund_gaps_equal_target():
    weights = {"A": 0.5, "B": 0.5}
    gaps = compute_fund_gaps(
        market_value_by_code={"A": 1000.0, "B": 4000.0},
        intra_weights=weights,
        total_value=10000.0,
        category_target=0.4,
    )
    assert gaps["A"] == 1000.0
    assert gaps["B"] == 0.0


def test_allocate_category_add_proportional():
    amounts = allocate_category_add(
        category_gap_amount=1000.0,
        fund_gaps={"A": 600.0, "B": 400.0},
    )
    assert amounts["A"] == 600.0
    assert amounts["B"] == 400.0


def test_allocate_category_add_rounding_fixes_sum():
    amounts = allocate_category_add(
        category_gap_amount=100.0,
        fund_gaps={"A": 1.0, "B": 1.0, "C": 1.0},
    )
    assert round(sum(amounts.values()), 2) == 100.0


def test_is_performance_blocked_add_reduce():
    assert is_performance_blocked_add({"signal_type": "reduce", "reasons": []}) is True


def test_is_performance_blocked_add_watch_with_rule():
    assert (
        is_performance_blocked_add(
            {
                "signal_type": "watch",
                "reasons": [{"layer": "performance", "rule": "sharpe_1y", "detail": "x"}],
            }
        )
        is True
    )


def test_is_performance_blocked_add_hold():
    assert is_performance_blocked_add({"signal_type": "hold", "reasons": []}) is False
