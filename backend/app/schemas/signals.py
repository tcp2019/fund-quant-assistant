from datetime import datetime

from pydantic import BaseModel, Field


class SignalReason(BaseModel):
    layer: str
    rule: str
    detail: str
    category: str | None = None
    category_label: str | None = None


class SignalOut(BaseModel):
    id: int
    snapshot_id: int
    fund_code: str = ""
    fund_name: str | None = None
    category: str | None = None
    category_label: str | None = None
    signal_type: str
    score: float
    strength: int = Field(ge=1, le=5)
    reasons: list[SignalReason]
    suggested_amount: float
    created_at: datetime


class SignalsListOut(BaseModel):
    snapshot_id: int | None
    signals: list[SignalOut]
