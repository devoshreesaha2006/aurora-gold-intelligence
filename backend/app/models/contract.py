from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, Date
from backend.app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class Contract(Base):
    """
    MCX Commodity Contract Specification.
    Defines physical trading mechanics: lot size, quote unit, and purity.
    """
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(30), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    trading_unit = Column(String(50), nullable=False)
    trading_unit_grams = Column(Float, nullable=False)
    quote_unit = Column(String(50), nullable=False)
    quote_unit_grams = Column(Float, nullable=False)
    purity = Column(Integer, nullable=False)          # e.g., 995 or 999
    purity_factor = Column(Float, nullable=False)     # e.g., 0.995 or 0.999
    expiry_window = Column(String(50), nullable=True) # e.g., "3rd-5th"
    listing_date = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
