from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ContractBase(BaseModel):
    symbol: str = Field(..., description="Contract ticker symbol, e.g. GOLDM")
    name: str = Field(..., description="Human-readable contract name")
    trading_unit: str = Field(..., description="e.g. 100 grams")
    trading_unit_grams: float = Field(..., gt=0, description="Total physical grams per lot")
    quote_unit: str = Field(..., description="e.g. 10 grams")
    quote_unit_grams: float = Field(..., gt=0, description="Quoted unit in grams")
    purity: int = Field(..., ge=900, le=1000, description="Fineness per 1000 (e.g. 995, 999)")
    purity_factor: float = Field(..., gt=0, le=1.0, description="Purity expressed as decimal, e.g. 0.995")
    expiry_window: Optional[str] = Field(None, description="e.g. 3rd-5th or 27th-31st")
    listing_date: Optional[date] = None
    is_active: bool = True
    description: Optional[str] = None


class ContractCreate(ContractBase):
    pass


class ContractRead(ContractBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
