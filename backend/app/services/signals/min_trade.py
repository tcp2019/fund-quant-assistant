def apply_min_trade_to_signals(signals: list[dict], min_cny: float) -> list[dict]:
    if min_cny <= 0:
        return signals

    for signal in signals:
        amount = signal.get("suggested_amount", 0.0)
        if amount == 0 or abs(amount) >= min_cny:
            continue
        signal["suggested_amount"] = 0.0
        reasons = signal.setdefault("reasons", [])
        reasons.append(
            {
                "layer": "aggregate",
                "rule": "below_min_trade",
                "detail": f"建议金额 ¥{abs(amount):.0f} 低于最小交易额 ¥{min_cny:.0f}，暂不执行",
            }
        )
    return signals
