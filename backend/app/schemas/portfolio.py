from datetime import datetime

from pydantic import BaseModel


class HoldingIn(BaseModel):
    fund_code: str
    fund_name: str
    shares: float
    cost_price: float
    market_value: float
    profit: float = 0.0
    profit_rate: float = 0.0
    platform: str = "unknown"
    hold_days: int | None = None


class SnapshotCreate(BaseModel):
    holdings: list[HoldingIn]
    source: str = "manual"
    note: str = ""


class HoldingOut(HoldingIn):
    weight_pct: float


class OverviewOut(BaseModel):
    snapshot_id: int | None
    total_value: float
    total_cost: float
    total_profit: float
    total_profit_rate: float
    holdings: list[HoldingOut]


class SnapshotSummaryOut(BaseModel):
    id: int
    created_at: datetime
    source: str
    total_value: float


class SnapshotsListOut(BaseModel):
    snapshots: list[SnapshotSummaryOut]
