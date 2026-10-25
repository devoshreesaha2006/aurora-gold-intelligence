from datetime import date
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.common import StandardResponse
from backend.app.schemas.analytics import (
    PairSpreadResponse, RadarResponse, EventsResponse, DistributionResponse
)
from backend.app.services.analytics_service import (
    RelativeValueAnalyticsService, parse_pair, VALID_PAIR_STRINGS, VALID_PAIRS
)

router = APIRouter(prefix="/analytics", tags=["Relative-Value Analytics Engine"])


@router.get("/spreads", response_model=StandardResponse[PairSpreadResponse])
def get_pairwise_spreads(
    pair: str = Query("GOLDM-GOLDPETAL", description=f"Pair combination, e.g. {', '.join(VALID_PAIR_STRINGS)}"),
    window: int = Query(30, ge=2, le=365, description="Lookback rolling window in trading days"),
    start_date: Optional[date] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """
    Returns the eligible stored time-series of normalized price spreads for a contract
    pair. Includes rolling mean, sample standard deviation (ddof=1), rolling Z-score,
    empirical percentile rank, observed volume/OI where available, and expiry DTE
    without look-ahead bias. Returned observations may be historical, not live.
    """
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_date must be on or before end_date.")

    try:
        leg_a, leg_b, is_inverted = parse_pair(pair)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    service = RelativeValueAnalyticsService(db)
    spread_data = service.calculate_pairwise_spread_series(
        leg_a=leg_a,
        leg_b=leg_b,
        window_days=window,
        start_date=start_date,
        end_date=end_date,
        invert_spread=is_inverted
    )

    return StandardResponse(
        success=True,
        data=spread_data,
        message=f"Retrieved {spread_data.total_points} pairwise spread observations for {pair}."
    )


@router.get("/radar", response_model=StandardResponse[RadarResponse])
def get_opportunity_radar(
    window: int = Query(30, ge=2, le=365, description="Lookback window in days"),
    evaluation_date: Optional[date] = Query(None, description="Snapshot date (defaults to latest available)"),
    db: Session = Depends(get_db)
):
    """
    Returns a relative-value radar across all 6 canonical MCX Gold pairs using the
    latest eligible observations available in storage (or the requested evaluation date).
    This is not a claim of live market connectivity. Includes deviation intensities,
    heuristic ranking scores, trap-risk scores, and rule-based classifications.
    """
    service = RelativeValueAnalyticsService(db)
    radar_data = service.get_radar_summary(
        window_days=window,
        evaluation_date=evaluation_date
    )

    return StandardResponse(
        success=True,
        data=radar_data,
        message=f"Computed relative-value radar matrix across 6 MCX Gold pairs for {radar_data.evaluation_date}."
    )


@router.get("/events", response_model=StandardResponse[EventsResponse])
def get_relative_value_events(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by classification (Investigate, Watch, Cost-Blocked, Expiry-Risk)"),
    pair: Optional[str] = Query(None, description="Filter by contract pair"),
    min_z: Optional[float] = Query(None, ge=0.0, description="Minimum absolute Z-score threshold"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Returns eligible stored relative-value events with evidence trails: normalized
    spread, Z-score, empirical percentile, estimated friction hurdle, observed
    volume/OI where available, DTE, and plain-language decision rules. Event dates
    may be historical; this endpoint does not imply a live feed.
    """
    if pair:
        try:
            parse_pair(pair)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        pair = pair.strip().upper().replace("/", "-").replace("_", "-")

    if status_filter:
        allowed_statuses = {"investigate", "watch", "cost-blocked", "expiry-risk", "no signal"}
        if status_filter.strip().lower() not in allowed_statuses:
            allowed = ", ".join(sorted(allowed_statuses))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported status '{status_filter}'. Allowed values: {allowed}.",
            )

    service = RelativeValueAnalyticsService(db)
    events_data = service.get_events(
        status=status_filter.strip() if status_filter else None,
        pair=pair,
        min_z=min_z,
        limit=limit,
        offset=offset
    )

    return StandardResponse(
        success=True,
        data=events_data,
        message=f"Found {events_data.total_events} relative-value investigation events."
    )


@router.get("/distribution", response_model=StandardResponse[DistributionResponse])
def get_spread_distribution(
    pair: str = Query("GOLDM-GOLDPETAL", description="Pair name"),
    window: int = Query(365, ge=5, le=1000, description="Maximum synchronized trading observations"),
    bins: int = Query(15, ge=5, le=50, description="Histogram bins count"),
    db: Session = Depends(get_db)
):
    """
    Returns historical spread distribution, skewness, kurtosis, empirical frequency bins,
    and theoretical Gaussian PDF curve for the specified pair.
    """
    try:
        # Validate pair names here so malformed requests return a clear 400, not a 500.
        parse_pair(pair)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    service = RelativeValueAnalyticsService(db)
    dist_data = service.get_spread_distribution(
        pair=pair.strip().upper().replace("/", "-").replace("_", "-"),
        window_days=window,
        num_bins=bins
    )

    return StandardResponse(
        success=True,
        data=dist_data,
        message=f"Generated empirical distribution and Gaussian curve for {pair}."
    )
