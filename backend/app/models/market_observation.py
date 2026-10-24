from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, UniqueConstraint, false
)
from backend.app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class MarketObservation(Base):
    """
    Normalized commodity settlement / trade observation.
    Captures both raw quoted prices and standardized fine-gold price equivalents.
    Tracks contracts explicitly by expiry_date rather than synthetic continuous series.
    """
    __tablename__ = "market_observations"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(30), ForeignKey("contracts.symbol"), index=True, nullable=False)
    trade_date = Column(Date, index=True, nullable=False)
    expiry_date = Column(Date, index=True, nullable=False)

    # Raw market metrics (Quoted in contract quotation basis)
    open_price = Column(Float, nullable=True)
    high_price = Column(Float, nullable=True)
    low_price = Column(Float, nullable=True)
    close_price = Column(Float, nullable=False) # Settlement / Close price
    volume = Column(Integer, default=0, nullable=False) # Traded lots
    open_interest = Column(Integer, default=0, nullable=False) # Open contracts
    # Keep zero distinct from an omitted CSV/provider field. Legacy rows are
    # backfilled conservatively by the additive startup schema upgrade.
    volume_observed = Column(Boolean, default=False, server_default=false(), nullable=False)
    open_interest_observed = Column(Boolean, default=False, server_default=false(), nullable=False)

    # Normalized metrics (Common comparable basis across all gold contracts)
    # 1. Pure fine-gold price per gram: (Quoted Price / Quoted Grams) / (Purity / 1000)
    normalized_price_per_gram = Column(Float, nullable=False)
    # 2. Benchmark 10g 995 basis: normalized_price_per_gram * 10 * 0.995
    normalized_price_10g_basis = Column(Float, nullable=False)

    # Ingestion provenance & transparency flags
    data_source = Column(String(50), default="csv_upload", nullable=False)
    is_synthetic = Column(Boolean, default=False, nullable=False)
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=True)
    # Exchange/provider timestamp is distinct from local persistence time.
    provider_timestamp = Column(DateTime(timezone=True), nullable=True, index=True)
    # Set only by the authorized adapter after a confirmed provider response.
    is_provider_verified = Column(Boolean, default=False, server_default=false(), nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Prevent accidental duplicates of the exact same contract observation on the same trade date & expiry
    __table_args__ = (
        UniqueConstraint("symbol", "trade_date", "expiry_date", name="uq_contract_trade_expiry"),
    )
