from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.funds import FundCandidateOut


class SignalReason(BaseModel):
    layer: str
    rule: str
    detail: str
    category: str | None = None
    category_label: str | None = None
    paired_fund_code: str | None = None
    paired_fund_name: str | None = None
    correlation: float | None = None


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
    interpretation: str | None = None
    created_at: datetime
    candidates: list[FundCandidateOut] = []


class InterpretRequest(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    model: str | None = None


class InterpretOut(BaseModel):
    signal_id: int
    interpretation: str | None
    cached: bool


class SignalsListOut(BaseModel):
    snapshot_id: int | None
    signals: list[SignalOut]
