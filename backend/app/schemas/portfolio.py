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


class HoldingThemeOut(BaseModel):
    theme: str
    label: str


class SnapshotCreate(BaseModel):
    holdings: list[HoldingIn]
    source: str = "manual"
    note: str = ""


class HoldingOut(HoldingIn):
    weight_pct: float
    current_value: float = 0.0
    current_profit: float = 0.0
    nav_date: str | None = None
    themes: list[HoldingThemeOut] = []


class CategoryAllocationOut(BaseModel):
    category: str
    label: str
    weight_pct: float
    market_value: float


class ThemeAllocationOut(BaseModel):
    theme: str
    label: str
    weight_pct: float
    market_value: float


class OverviewOut(BaseModel):
    snapshot_id: int | None
    total_value: float
    total_cost: float
    total_profit: float
    total_profit_rate: float
    current_total_value: float = 0.0
    current_total_profit: float = 0.0
    current_total_profit_rate: float = 0.0
    nav_date: str | None = None
    holdings: list[HoldingOut]
    category_allocation: list[CategoryAllocationOut] = []
    theme_allocation: list[ThemeAllocationOut] = []
    top_holdings: list[HoldingOut] = []
    concentration_top5_pct: float = 0.0
    data_as_of_date: str | None = None


class SnapshotSummaryOut(BaseModel):
    id: int
    created_at: datetime
    source: str
    total_value: float


class SnapshotsListOut(BaseModel):
    snapshots: list[SnapshotSummaryOut]
