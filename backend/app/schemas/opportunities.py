from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.funds import FundCandidateOut


class StructuralActionOut(BaseModel):
    action: Literal["consolidate", "rebalance_review"]
    category: str
    category_label: str
    detail: str
    fund_count: int | None = None
    blocked_buy_count: int | None = None


class ActionItemOut(BaseModel):
    action: Literal["sell", "add_holding", "explore"]
    fund_code: str = ""
    fund_name: str | None = None
    category: str | None = None
    category_label: str | None = None
    suggested_amount: float
    score: float
    strength: int = Field(ge=1, le=5)
    reason_summary: str
    signal_id: int | None = None
    candidates: list[FundCandidateOut] = []


class HotThemeOut(BaseModel):
    theme: str
    label: str
    heat_score: float
    return_1m_median: float | None = None
    portfolio_weight_pct: float = 0.0
    aligned_gap: bool = False
    aligned_category_label: str | None = None
    candidates: list[FundCandidateOut] = []


class OpportunitiesOut(BaseModel):
    snapshot_id: int | None
    data_as_of_date: str | None = None
    structural_actions: list[StructuralActionOut] = Field(default_factory=list)
    sell_actions: list[ActionItemOut]
    buy_actions: list[ActionItemOut]
    explore_actions: list[ActionItemOut]
    hot_themes: list[HotThemeOut]
