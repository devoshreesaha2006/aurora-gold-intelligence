from datetime import date, datetime, timezone
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator
from backend.app.schemas.common import PaginationMeta


class MarketStatusRead(BaseModel):
    """
    Market status and data connectivity metrics.
    Explicitly informs the UI whether data is test, synthetic, unverified user CSV,
    disconnected, or provider-verified live feed.
    """
    market_open: Optional[bool] = Field(
        None,
        description="MCX session state when an authoritative calendar is configured; otherwise unknown",
    )
    market_session_status: str = Field(
        "unknown",
        description="Authoritative MCX session state, or unknown when no calendar source is configured",
    )
    data_mode: str = Field(..., description="demo_synthetic, staged_csv, test_data, live_feed_disconnected, or verified live_feed_authorized")
    provider_name: str = Field(..., description="Active market data provider name")
    is_live_connected: bool = Field(False, description="True only if verified live broker/exchange feed active")
    total_contracts_tracked: int
    total_observations: int
    last_ingestion_at: Optional[datetime] = None
    latest_trade_date: Optional[date] = None
    server_time: datetime
    data_freshness_label: str
    # Additive feed-health fields. Existing response fields remain intact.
    feed_status: str = "UNAVAILABLE"
    connection_state: str = "disconnected"
    authentication_state: str = "unknown"
    last_observation_received_at: Optional[datetime] = None
    last_provider_timestamp: Optional[datetime] = None
    feed_freshness_seconds: Optional[int] = None
    data_provenance: str = "unverified"
    provider_error: Optional[str] = None

    @field_validator("last_observation_received_at", "last_provider_timestamp", mode="before")
    @classmethod
    def normalize_utc_timestamp(cls, value):
        # SQLite does not round-trip timezone metadata; provider timestamps are
        # persisted as UTC and need an explicit UTC offset in API responses.
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


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
    provider_timestamp: Optional[datetime] = None
    is_provider_verified: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("provider_timestamp", mode="before")
    @classmethod
    def normalize_provider_timestamp(cls, value):
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class MarketPriceList(BaseModel):
    items: List[MarketPriceItem]
    pagination: PaginationMeta
    data_mode: str
