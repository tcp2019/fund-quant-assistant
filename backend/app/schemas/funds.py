from pydantic import BaseModel, Field


class FundSearchResultOut(BaseModel):
    fund_code: str
    fund_name: str
    fund_type: str


class FundSearchOut(BaseModel):
    results: list[FundSearchResultOut]
    catalog_ready: bool


class CatalogRefreshOut(BaseModel):
    count: int


class FundCandidateOut(BaseModel):
    fund_code: str
    fund_name: str
    category: str
    return_1y: float | None = None
    return_1m: float | None = None
    return_1w: float | None = None
    as_of_date: str = ""
    data_source: str


class ThemeCandidatesOut(BaseModel):
    theme: str
    label: str
    sort_by: str
    candidates: list[FundCandidateOut]
