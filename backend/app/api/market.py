from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.common import StandardResponse, PaginationMeta
from backend.app.schemas.market import MarketStatusRead, MarketPriceItem, MarketPriceList
from backend.app.providers import get_market_provider
from backend.app.models.market_observation import MarketObservation

router = APIRouter(prefix="/market", tags=["Market Data"])


@router.get("/status", response_model=StandardResponse[MarketStatusRead])
def get_market_status(db: Session = Depends(get_db)):
    """
    Returns real-time data connectivity, provider mode, observations count,
    and data freshness timestamp.
    """
    provider = get_market_provider()
    status = provider.get_market_status(db)
    return StandardResponse(
        success=True,
        message="Market status retrieved",
        data=status
    )


@router.get("/prices", response_model=StandardResponse[MarketPriceList])
def get_market_prices(
    symbol: Optional[str] = Query(None, description="Filter by contract symbol (e.g. GOLDM)"),
    start_date: Optional[date] = Query(None, description="Start trade date (inclusive)"),
    end_date: Optional[date] = Query(None, description="End trade date (inclusive)"),
    limit: int = Query(50, ge=1, le=1000, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: Session = Depends(get_db)
):
    """
    Returns historical observations with both quoted prices and fine-gold normalized metrics.
    Supports filtering by contract symbol and trade date bounds.
    """
    query = db.query(MarketObservation)

    if symbol:
        clean_symbol = symbol.strip().upper()
        query = query.filter(MarketObservation.symbol == clean_symbol)

    if start_date:
        query = query.filter(MarketObservation.trade_date >= start_date)

    if end_date:
        query = query.filter(MarketObservation.trade_date <= end_date)

    total = query.count()
    items = (
        query.order_by(MarketObservation.trade_date.desc(), MarketObservation.symbol.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    provider = get_market_provider()
    status = provider.get_market_status(db)

    price_items = [MarketPriceItem.model_validate(item) for item in items]

    data_payload = MarketPriceList(
        items=price_items,
        pagination=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + len(items) < total)
        ),
        data_mode=status.data_mode
    )

    return StandardResponse(
        success=True,
        message=f"Retrieved {len(items)} price observations",
        data=data_payload
    )
