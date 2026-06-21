from pydantic import BaseModel


class CorrelationOut(BaseModel):
    snapshot_id: int | None
    labels: list[str]
    matrix: list[list[float]]
    period_days: int


class RiskOut(BaseModel):
    snapshot_id: int | None
    volatility: float | None
    sharpe: float | None
    max_dd: float | None
    period_days: int
