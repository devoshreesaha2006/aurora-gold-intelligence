from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.common import PaginationMeta


class MarketStatusRead(BaseModel):
    """
    Market status and data connectivity metrics.
    Explicitly informs the UI whether data is synthetic demo, staged CSV, or live feed.
    """
    market_open: bool = Field(..., description="Estimated market session status")
    data_mode: str = Field(..., description="demo_synthetic, staged_csv, or live_feed_authorized")
    provider_name: str = Field(..., description="Active market data provider name")
    is_live_connected: bool = Field(False, description="True only if verified live broker/exchange feed active")
    total_contracts_tracked: int
    total_observations: int
    last_ingestion_at: Optional[datetime] = None
    latest_trade_date: Optional[date] = None
    server_time: datetime
    data_freshness_label: str


class MarketPriceItem(BaseModel):
    id: int
    symbol: str
    trade_date: date
    expiry_date: date
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: float
    volume: int
    open_interest: int
    normalized_price_per_gram: float
    normalized_price_10g_basis: float
    data_source: str
    is_synthetic: bool
    import_batch_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarketPriceList(BaseModel):
    items: List[MarketPriceItem]
    pagination: PaginationMeta
    data_mode: str
