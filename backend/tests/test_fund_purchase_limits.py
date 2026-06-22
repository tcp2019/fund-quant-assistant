from app.services.fund_purchase_limits import (
    apply_purchase_limits_to_signal,
    is_purchase_suspended,
    is_restrictive_daily_limit,
    normalize_daily_limit,
    parse_purchase_record,
)


def test_normalize_daily_limit_treats_large_values_as_unlimited():
    assert normalize_daily_limit(20.0) == 20.0
    assert normalize_daily_limit(1e11) is None
    assert normalize_daily_limit(0.0) == 0.0


def test_is_restrictive_daily_limit():
    assert is_restrictive_daily_limit(20.0) is True
    assert is_restrictive_daily_limit(500.0) is True
    assert is_restrictive_daily_limit(501.0) is False
    assert is_restrictive_daily_limit(50_000.0) is False
    assert is_restrictive_daily_limit(None) is False


def test_is_purchase_suspended():
    assert is_purchase_suspended("暂停申购") is True
    assert is_purchase_suspended("限大额") is False


def test_apply_purchase_limits_downgrades_add_when_daily_limit_blocks():
    signal = {
        "fund_code": "012922",
        "signal_type": "add",
        "score": 18.3,
        "strength": 2,
        "suggested_amount": 1703.0,
        "reasons": [
            {
                "layer": "rebalance",
                "rule": "category_underweight",
                "detail": "股票型低配 9.1%，建议增配 ¥52806",
            }
        ],
    }
    purchase_info = parse_purchase_record(
        {
            "purchase_status": "限大额",
            "purchase_min_amount": 10.0,
            "daily_purchase_limit": 20.0,
        }
    )

    updated = apply_purchase_limits_to_signal(signal, purchase_info)

    assert updated["signal_type"] == "watch"
    assert updated["suggested_amount"] == 20.0
    assert any(reason["rule"] == "purchase_limit_blocked" for reason in updated["reasons"])


def test_apply_purchase_limits_protects_reduce_on_restricted_fund():
    signal = {
        "fund_code": "012922",
        "signal_type": "reduce",
        "score": -30.0,
        "strength": 3,
        "suggested_amount": 0.0,
        "reasons": [
            {
                "layer": "concentration",
                "rule": "single_fund_concentration",
                "detail": "单只占比 30.0% 超过 25%，建议减仓分散风险",
            }
        ],
    }
    purchase_info = parse_purchase_record(
        {
            "purchase_status": "限大额",
            "purchase_min_amount": 10.0,
            "daily_purchase_limit": 20.0,
        }
    )

    updated = apply_purchase_limits_to_signal(signal, purchase_info)

    assert updated["signal_type"] == "watch"
    assert any(reason["rule"] == "redemption_hard_to_rebuy" for reason in updated["reasons"])


def test_apply_purchase_limits_keeps_performance_reduce():
    signal = {
        "fund_code": "012922",
        "signal_type": "reduce",
        "score": -45.0,
        "strength": 4,
        "suggested_amount": 0.0,
        "reasons": [
            {
                "layer": "performance",
                "rule": "excess_return_1y",
                "detail": "近1年超额收益 -12.0%，低于基准 5%",
            }
        ],
    }
    purchase_info = parse_purchase_record(
        {
            "purchase_status": "限大额",
            "purchase_min_amount": 10.0,
            "daily_purchase_limit": 20.0,
        }
    )

    updated = apply_purchase_limits_to_signal(signal, purchase_info)

    assert updated["signal_type"] == "reduce"
