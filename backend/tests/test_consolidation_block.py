from app.services.signals.action_classifier import classify_signal_action
from app.services.signals.engine import aggregate_signals


def test_overcrowded_category_blocks_intra_add_amounts():
    rebalance = [
        {
            "category": "stock",
            "signal_type": "add",
            "deviation_pct": 9.1,
            "suggested_amount": 10000.0,
            "detail": "股票型低配 9.1%",
        }
    ]
    fund_categories = {f"S{i:02d}": "stock" for i in range(12)}
    market_value_by_code = {code: 200.0 for code in fund_categories}
    overcrowded = {"stock"}

    results = aggregate_signals(
        rebalance,
        [],
        [],
        fund_categories,
        market_value_by_code=market_value_by_code,
        total_value=12000.0,
        category_targets={"stock": 0.4},
        intra_category_mode="equal",
        overcrowded_categories=overcrowded,
    )
    fund_results = [r for r in results if r["fund_code"]]
    assert all(r["suggested_amount"] == 0.0 for r in fund_results)
    assert any(
        reason.get("rule") == "consolidation_blocked_add"
        for r in fund_results
        for reason in r["reasons"]
    )
    category_adds = [r for r in results if not r["fund_code"] and r["signal_type"] == "add"]
    assert len(category_adds) == 1
    assert category_adds[0]["suggested_amount"] == 10000.0


def test_consolidation_blocked_not_add_holding():
    reasons = [
        {"layer": "rebalance", "rule": "category_underweight", "detail": "..."},
        {"layer": "aggregate", "rule": "consolidation_blocked_add", "detail": "..."},
    ]
    assert classify_signal_action("add", reasons, 1000.0, 25.0) == "watch"
