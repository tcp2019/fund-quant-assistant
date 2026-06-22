from pydantic import BaseModel


class SensitivitySignalOut(BaseModel):
    category: str
    signal_type: str
    deviation_pct: float
    suggested_amount: float


class SensitivityScenarioOut(BaseModel):
    threshold_pct: float
    triggered_categories: int
    signals: list[SensitivitySignalOut]


class SensitivityReportOut(BaseModel):
    snapshot_id: int | None
    total_value: float
    scenarios: list[SensitivityScenarioOut]


class SnapshotStatOut(BaseModel):
    snapshot_id: int
    created_at: str
    rebalance_triggers: int
    category_count_max: int


class SnapshotStatsOut(BaseModel):
    snapshots: list[SnapshotStatOut]
