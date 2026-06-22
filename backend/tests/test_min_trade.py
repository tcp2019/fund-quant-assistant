from app.services.signals.min_trade import apply_min_trade_to_signals


def test_min_trade_zeros_small_amounts():
    signals = [
        {"fund_code": "A", "suggested_amount": 200.0, "reasons": []},
        {"fund_code": "B", "suggested_amount": 800.0, "reasons": []},
    ]
    result = apply_min_trade_to_signals(signals, min_cny=500.0)
    assert result[0]["suggested_amount"] == 0.0
    assert result[1]["suggested_amount"] == 800.0
    assert any(r["rule"] == "below_min_trade" for r in result[0]["reasons"])
