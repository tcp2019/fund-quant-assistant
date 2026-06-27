"""Adaptive layer weights based on macro environment."""
DEFAULT_WEIGHTS = {"rebalance": 0.4, "concentration": 0.3, "performance": 0.3}
TIGHT_WEIGHTS = {"rebalance": 0.4, "concentration": 0.4, "performance": 0.2}
LOOSE_WEIGHTS = {"rebalance": 0.5, "concentration": 0.2, "performance": 0.3}


def get_adaptive_weights(environment: str) -> dict:
    if environment == "tight":
        return TIGHT_WEIGHTS
    elif environment == "loose":
        return LOOSE_WEIGHTS
    return DEFAULT_WEIGHTS
