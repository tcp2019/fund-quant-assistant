from typing import Literal

from pydantic import BaseModel, Field

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


IntraCategoryMode = Literal["equal", "pro_rata", "custom"]


class StrategyThresholds(BaseModel):
    rebalance_deviation_pct: float = Field(default=5.0, ge=0.1, le=50.0)
    rebalance_force_days: float = Field(default=365, ge=1, le=3650)
    single_fund_max_pct: float = Field(default=25.0, ge=5.0, le=100.0)
    correlation_max: float = Field(default=0.85, ge=0.0, le=1.0)


class StrategyOut(BaseModel):
    template_name: str
    target_weights: dict[str, float]
    thresholds: dict[str, float]
    intra_category_mode: str = "equal"
    fund_target_weights: dict[str, float] = Field(default_factory=dict)


class StrategyUpdateIn(BaseModel):
    template_name: str
    target_weights: dict[str, float] | None = None
    thresholds: StrategyThresholds | None = None
    intra_category_mode: IntraCategoryMode | None = None
    fund_target_weights: dict[str, float] | None = None
