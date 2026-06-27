from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class PortfolioSnapshot(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    source: str = "ocr"
    note: str = ""


class Holding(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    snapshot_id: int = Field(foreign_key="portfoliosnapshot.id", index=True)
    fund_code: str = Field(index=True)
    fund_name: str
    shares: float
    cost_price: float
    market_value: float
    profit: float = 0.0
    profit_rate: float = 0.0
    platform: str = "unknown"
    hold_days: Optional[int] = None


class OcrJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: str = "pending"  # pending | parsed | confirmed | failed
    image_paths: str = "[]"  # JSON array string
    parsed_json: str = "{}"
    confirmed_at: Optional[datetime] = None


class FundMetadata(SQLModel, table=True):
    code: str = Field(primary_key=True)
    name: str
    fund_type: str = "other"
    category: str = "other"
    benchmark_code: str = ""
    manager: str = ""
    purchase_status: str = ""
    purchase_min_amount: Optional[float] = None
    daily_purchase_limit: Optional[float] = None
    themes_json: str = "[]"
    user_themes_json: str = "[]"


class FundNavHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True)
    date: str = Field(index=True)
    nav: float
    acc_nav: float = 0.0


class FundMetricsCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True)
    as_of_date: str
    sharpe_1y: Optional[float] = None
    max_drawdown_1y: Optional[float] = None
    excess_return_1y: Optional[float] = None
    return_1y: Optional[float] = None
    peer_return_percentile_3m: Optional[float] = None
    computed_from: str = ""


class FundCatalog(SQLModel, table=True):
    code: str = Field(primary_key=True)
    name: str
    fund_type: str = ""
    pinyin_abbr: str = ""
    synced_at: datetime = Field(default_factory=datetime.utcnow)


class FundRankCache(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    category: str = Field(index=True)
    payload_json: str = "{}"
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class StrategyConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    template_name: str = "balanced"
    target_weights_json: str = "{}"
    thresholds_json: str = "{}"
    intra_category_mode: str = "equal"
    fund_target_weights_json: str = "{}"


class SignalRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    snapshot_id: int = Field(index=True)
    fund_code: str = ""
    signal_type: str  # reduce | add | hold | watch
    score: float
    strength: int
    reasons_json: str = "[]"
    suggested_amount: float = 0.0
    interpretation: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SyncLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    status: str = "running"  # running | done | partial | failed
    total_funds: int = 0
    success_funds: int = 0
    failed_funds: int = 0
    errors_json: str = "[]"
