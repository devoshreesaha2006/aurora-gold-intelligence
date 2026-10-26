from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.common import StandardResponse
from backend.app.services.analytics_service import parse_pair
from backend.app.services.term_structure_service import TermStructureService


router = APIRouter(prefix="/research", tags=["Research & Attribution"])


@router.get("/term-structure", response_model=StandardResponse[dict])
def get_term_structure(
    pair: str = Query("GOLDM-GOLDPETAL", description="Contract pair; either leg order is accepted"),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    db: Session = Depends(get_db),
):
    """Separate same-expiry spread movement from front-contract switch gaps."""
    try:
        parse_pair(pair)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date must be on or before end_date")
    data = TermStructureService(db).report(pair, start_date, end_date)
    return StandardResponse(
        success=True,
        data=data,
        message=("Expiry-aware term-structure report generated." if data["observations"] else
                 "No eligible synchronized observations are available for this pair and date window."),
    )
