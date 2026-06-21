from pydantic import BaseModel

from app.schemas.portfolio import HoldingIn


class OcrUploadRequest(BaseModel):
    text: str
    platform: str | None = None


class ParsedHoldingOut(BaseModel):
    fund_code: str
    fund_name: str
    shares: float
    cost_price: float
    market_value: float
    profit: float
    profit_rate: float
    platform: str
    confidence: float = 1.0


class OcrUploadResponse(BaseModel):
    job_id: int
    holdings: list[ParsedHoldingOut]
    warnings: list[str]


class OcrConfirmRequest(BaseModel):
    holdings: list[HoldingIn]


class OcrConfirmResponse(BaseModel):
    snapshot_id: int
