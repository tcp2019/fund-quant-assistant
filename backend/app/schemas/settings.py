DEFAULT_TEMPLATES = {
    "balanced": {
        "stock": 0.40,
        "bond": 0.30,
        "money": 0.15,
        "qdii": 0.10,
        "other": 0.05,
    },
    "conservative": {
        "stock": 0.20,
        "bond": 0.50,
        "money": 0.20,
        "qdii": 0.05,
        "other": 0.05,
    },
    "aggressive": {
        "stock": 0.60,
        "bond": 0.15,
        "money": 0.05,
        "qdii": 0.15,
        "other": 0.05,
    },
}

DEFAULT_THRESHOLDS = {
    "rebalance_deviation_pct": 5.0,
    "rebalance_force_days": 365,
    "single_fund_max_pct": 25.0,
    "correlation_max": 0.85,
}
