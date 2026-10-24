from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# -----------------------------------------------------------------------------
# Pairwise Spread Schemas
# -----------------------------------------------------------------------------

class PairSpreadPoint(BaseModel):
    trade_date: date
    expiry_date: Optional[date] = Field(None, description="Shared contract expiry matched across both pair legs")
    spread: float = Field(..., description="Normalized Spread (Leg A - Leg B) in ₹ per 10g benchmark basis")
    price_a: float = Field(..., description="Leg A normalized price (₹ per 10g)")
    price_b: float = Field(..., description="Leg B normalized price (₹ per 10g)")
    raw_price_a: float = Field(..., description="Leg A raw quoted close price")
    raw_price_b: float = Field(..., description="Leg B raw quoted close price")
    rolling_mean: Optional[float] = Field(None, description="Rolling mean spread over lookback window")
    rolling_std: Optional[float] = Field(None, description="Rolling sample standard deviation (ddof=1)")
    z_score: Optional[float] = Field(None, description="Rolling Z-score ((spread - mean) / std)")
    percentile_rank: Optional[float] = Field(None, description="Empirical percentile rank of spread within window (0-100%)")
    upper_2sigma: Optional[float] = None
    lower_2sigma: Optional[float] = None
    upper_1sigma: Optional[float] = None
    lower_1sigma: Optional[float] = None
    volume_a: Optional[int] = None
    volume_b: Optional[int] = None
    open_interest_a: Optional[int] = None
    open_interest_b: Optional[int] = None
    dte_a: Optional[int] = Field(None, description="Leg A days to expiry")
    dte_b: Optional[int] = Field(None, description="Leg B days to expiry")
    status: str = Field("valid", description="Calculation status: 'valid', 'insufficient_history', 'zero_variance'")


class PairSpreadResponse(BaseModel):
    pair: str
    leg_a: str
    leg_b: str
    window_days: int
    total_points: int
    data_points: List[PairSpreadPoint]


# -----------------------------------------------------------------------------
# Radar & Opportunity Summary Schemas
# -----------------------------------------------------------------------------

class CostHurdleAssumptions(BaseModel):
    stt_rate_pct: float = Field(0.01, description="Securities/Commodities Transaction Tax (0.01% on sell side)")
    exchange_fee_pct: float = Field(0.0025, description="MCX turnover + SEBI regulatory charge")
    brokerage_per_10g: float = Field(2.50, description="Estimated brokerage hurdle in ₹ per 10g")
    slippage_buffer_per_10g: float = Field(15.00, description="Bid-ask half-spread / execution slippage buffer in ₹ per 10g")
    total_roundtrip_cost_per_10g: float = Field(..., description="Total estimated hurdle in ₹ per 10g")


class PairRadarItem(BaseModel):
    pair: str
    leg_a: str
    leg_b: str
    trade_date: Optional[date] = None
    expiry_date: Optional[date] = None
    spread: Optional[float] = None
    rolling_mean: Optional[float] = None
    rolling_std: Optional[float] = None
    z_score: Optional[float] = None
    percentile_rank: Optional[float] = None
    deviation_intensity: Optional[float] = Field(None, description="0-100 scale for radar visualization (|Z| mapped to 0-100); null without eligible observations")
    historical_norm: Optional[float] = Field(None, description="Median prior-session deviation intensity (0-100), when history exists")
    friction_boundary: Optional[float] = Field(None, description="Cost hurdle mapped to current rolling standard deviation (0-100), when defined")
    classification: str = Field(..., description="Investigate, Watch, Cost-Blocked, Expiry-Risk, or No Signal")
    opportunity_score: Optional[float] = Field(None, description="0-100 composite opportunity rating; null without an analyzable observation")
    trap_risk_score: Optional[float] = Field(None, description="0-100 composite execution/trap risk rating; null without an analyzable observation")
    is_expiry_risk: bool = False
    is_cost_blocked: bool = False
    is_liquidity_trap: bool = False
    dte_min: Optional[int] = None
    min_volume: Optional[int] = None
    min_open_interest: Optional[int] = None
    estimated_cost_hurdle: float
    gross_edge: Optional[float] = None
    net_edge: Optional[float] = None
    reason: str


class RadarResponse(BaseModel):
    evaluation_date: Optional[date] = None
    window_days: int
    pairs: List[PairRadarItem]
    active_investigations_count: int
    cost_blocked_count: int
    expiry_risk_count: int
    watch_count: int


# -----------------------------------------------------------------------------
# Event Investigation Dossier Schemas
# -----------------------------------------------------------------------------

class EventEvidenceTrail(BaseModel):
    spread: Optional[float] = None
    benchmark_basis: str = "₹ per 10g (995 fine gold equivalent)"
    rolling_mean: Optional[float] = None
    rolling_std: Optional[float] = None
    z_score: Optional[float] = None
    percentile_rank: Optional[float] = None
    gross_edge: Optional[float] = None
    net_edge: Optional[float] = None
    dte_a: Optional[int] = None
    dte_b: Optional[int] = None
    volume_a: int = 0
    volume_b: int = 0
    open_interest_a: int = 0
    open_interest_b: int = 0
    cost_hurdle: float
    rule_triggered: str
    caveats: List[str] = Field(default_factory=list)


class RelativeValueEvent(BaseModel):
    event_id: str
    pair: str
    leg_a: str
    leg_b: str
    trade_date: date
    severity: str = Field(..., description="critical, high, medium, low")
    classification: str = Field(..., description="Investigate, Watch, Cost-Blocked, Expiry-Risk, No Signal")
    opportunity_score: float
    trap_risk_score: float
    summary: str
    evidence: EventEvidenceTrail


class EventsResponse(BaseModel):
    total_events: int
    items: List[RelativeValueEvent]


# -----------------------------------------------------------------------------
# Historical Distribution Schemas
# -----------------------------------------------------------------------------

class DistributionResponse(BaseModel):
    pair: str
    window_days: int
    sample_size: int
    expiry_policy: str = "Each point matches the same trade date and expiry; the nearest shared expiry is selected per session, so expiry can roll across history."
    evaluation_date: Optional[date] = None
    expiry_date: Optional[date] = None
    mean: Optional[float] = None
    sigma: Optional[float] = None
    median: Optional[float] = None
    skewness: Optional[float] = None
    kurtosis: Optional[str] = None
    current_spread: Optional[float] = None
    current_z_score: Optional[str] = None
    bins: List[float]
    frequencies: List[int]
    gaussian_pdf: List[float]
    status: str = "valid"
