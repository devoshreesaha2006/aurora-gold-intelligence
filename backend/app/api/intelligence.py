"""Historical-data intelligence endpoints for explainability and scenario analysis.

All calculations use eligible stored observations; outputs are research simulations, not live quotes or forecasts.
"""
from datetime import date, timedelta
from typing import Optional, List
from math import isfinite
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.schemas.common import StandardResponse
from backend.app.services.analytics_service import RelativeValueAnalyticsService, parse_pair
from backend.app.services.backtest_service import BacktestService
from backend.app.schemas.backtest import BacktestRequest

router = APIRouter(prefix="/intelligence", tags=["Historical Intelligence"])


class ScenarioRequest(BaseModel):
    pair: str = "GOLDM-GOLDPETAL"
    window: int = Field(default=30, ge=5, le=365)
    units: int = Field(default=1, ge=1, le=10000)
    spread_move_pct: float = Field(default=1.0, ge=-100, le=100)
    transaction_cost_per_10g: float = Field(default=10.31, ge=0, le=100000)
    slippage_per_10g: float = Field(default=15.0, ge=0, le=100000)
    holding_days: int = Field(default=5, ge=1, le=365)


class ScenarioResult(BaseModel):
    pair: str
    evaluation_date: Optional[date] = None
    expiry_date: Optional[date] = None
    current_spread: Optional[float] = None
    assumed_spread_change: Optional[float] = None
    units: int
    gross_pnl: Optional[float] = None
    estimated_costs: float
    estimated_net_pnl: Optional[float] = None
    break_even_move_pct: Optional[float] = None
    holding_days: int
    status: str
    assumptions: List[str]


class WalkForwardRequest(BaseModel):
    pair: str = "GOLDM-GOLDPETAL"
    window: int = Field(default=30, ge=5, le=365)
    train_fraction: float = Field(default=0.7, gt=0.5, lt=0.9)
    entry_z: float = Field(default=2.0, ge=0.5, le=5)
    transaction_cost_per_10g: float = Field(default=10.31, ge=0, le=100000)
    slippage_per_10g: float = Field(default=15.0, ge=0, le=100000)
    units: int = Field(default=1, ge=1, le=10000)


def _pair(value: str):
    try:
        a, b, inverted = parse_pair(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return a, b, inverted, f"{b}-{a}" if inverted else f"{a}-{b}"


def _select_training_threshold(training_z_scores: List[Optional[float]], entry_z_floor: float) -> float:
    """Choose a training-only threshold while honoring the user's configured minimum."""
    abs_z = sorted(
        abs(value)
        for value in training_z_scores
        if value is not None and isfinite(value)
    )
    if not abs_z:
        return entry_z_floor
    training_quantile = abs_z[int(0.9 * (len(abs_z) - 1))]
    return max(entry_z_floor, min(3.0, training_quantile))


@router.get("/explain")
def explain_opportunity(
    pair: str = Query("GOLDM-GOLDPETAL"),
    window: int = Query(30, ge=2, le=365),
    evaluation_date: Optional[date] = None,
    db: Session = Depends(get_db),
):
    """Explain a Radar classification with its actual calculated fields and rule evidence."""
    _a, _b, _inv, canonical_pair = _pair(pair)
    radar = RelativeValueAnalyticsService(db).get_radar_summary(window_days=window, evaluation_date=evaluation_date)
    item = next((row for row in radar.pairs if row.pair == canonical_pair), None)
    if item is None:
        raise HTTPException(status_code=404, detail="No eligible historical observations are available for this pair/date.")
    evidence = [
        {"factor": "Statistical deviation", "value": item.z_score, "unit": "z-score",
         "effect": "Elevated" if item.z_score is not None and abs(item.z_score) >= 1.5 else "Not elevated or unavailable",
         "available": item.z_score is not None},
        {"factor": "Historical percentile", "value": item.percentile_rank, "unit": "percentile",
         "effect": "Extreme" if item.percentile_rank is not None and (item.percentile_rank >= 95 or item.percentile_rank <= 5) else "Not extreme or unavailable",
         "available": item.percentile_rank is not None},
        {"factor": "Estimated net edge", "value": item.net_edge, "unit": "₹ per 10g",
         "effect": "Above estimated cost hurdle" if item.net_edge is not None and item.net_edge > 0 else "Not above hurdle or unavailable",
         "available": item.net_edge is not None},
        {"factor": "Days to expiry", "value": item.dte_min, "unit": "days",
         "effect": "Expiry risk" if item.is_expiry_risk else "No expiry-risk flag or unavailable",
         "available": item.dte_min is not None},
        {"factor": "Observed liquidity", "value": item.min_volume, "unit": "lots (minimum leg)",
         "effect": "Liquidity trap flag" if item.is_liquidity_trap else "No liquidity-trap flag or unavailable",
         "available": item.min_volume is not None},
    ]
    caveats = []
    if item.min_volume is None or item.min_open_interest is None:
        caveats.append("Liquidity evidence is incomplete; missing values are not treated as healthy liquidity.")
    if item.trade_date:
        caveats.append("Snapshot uses stored historical observations dated " + str(item.trade_date) + "; this is not a live signal.")
    caveats.append("Opportunity and trap scores are heuristic rule-based indicators, not probabilities of profit.")
    return StandardResponse(success=True, message="Explainability assembled from the existing Radar calculation.", data={
        "pair": item.pair, "classification": item.classification, "reason": item.reason,
        "evaluation_date": radar.evaluation_date,
        "trade_date": item.trade_date, "expiry_date": item.expiry_date,
        "opportunity_score": item.opportunity_score, "trap_risk_score": item.trap_risk_score,
        "spread": item.spread, "rolling_mean": item.rolling_mean, "z_score": item.z_score,
        "percentile_rank": item.percentile_rank, "gross_edge": item.gross_edge, "net_edge": item.net_edge,
        "estimated_cost_hurdle": item.estimated_cost_hurdle, "evidence": evidence, "caveats": caveats,
        "data_mode": "user-imported historical observations; not provider-verified"
    })


@router.post("/what-if", response_model=StandardResponse[ScenarioResult])
def what_if_scenario(request: ScenarioRequest, db: Session = Depends(get_db)):
    """Apply a user-entered spread move to the latest historical spread; never predicts a future move."""
    a, b, inverted, canonical_pair = _pair(request.pair)
    series = RelativeValueAnalyticsService(db).calculate_pairwise_spread_series(
        leg_a=a, leg_b=b, window_days=request.window, invert_spread=inverted
    )
    if not series.data_points:
        raise HTTPException(status_code=422, detail="No eligible synchronized historical data for this pair.")
    latest = series.data_points[-1]
    if latest.spread is None or not isfinite(latest.spread):
        raise HTTPException(status_code=422, detail="Latest historical spread is not usable for scenario analysis.")
    change = abs(latest.spread) * request.spread_move_pct / 100.0
    gross = change * request.units
    costs = (request.transaction_cost_per_10g + request.slippage_per_10g) * 2 * request.units
    net = gross - costs
    break_even = (costs / (abs(latest.spread) * request.units) * 100.0) if latest.spread else None
    result = ScenarioResult(
        pair=canonical_pair, evaluation_date=latest.trade_date, expiry_date=latest.expiry_date,
        current_spread=latest.spread, assumed_spread_change=change, units=request.units,
        gross_pnl=round(gross, 2), estimated_costs=round(costs, 2),
        estimated_net_pnl=round(net, 2), break_even_move_pct=round(break_even, 4) if break_even is not None else None,
        holding_days=request.holding_days, status="hypothetical_scenario",
        assumptions=[
            f"Assumes a spread move of {request.spread_move_pct}% of the absolute latest historical spread; direction is assumed favourable.",
            f"Holding period is a user-selected {request.holding_days} calendar day(s); no future observations are used.",
            f"Entered costs: transaction ₹{request.transaction_cost_per_10g:.2f}/10g + slippage ₹{request.slippage_per_10g:.2f}/10g; round-trip per unit ₹{(request.transaction_cost_per_10g + request.slippage_per_10g) * 2:.2f}; total for {request.units} unit(s) ₹{costs:.2f}.",
            "Costs are charged as a round-trip per unit from the user-configured transaction-cost and slippage assumptions.",
            "P&L is a simplified normalized ₹ per 10g illustration; it excludes margin, taxes not represented in inputs, and contract-specific execution effects.",
            "This is not a forecast, recommendation, or executable quote."
        ],
    )
    return StandardResponse(success=True, message="Hypothetical scenario calculated from the latest eligible historical spread.", data=result)


@router.post("/walk-forward")
def walk_forward_validation(request: WalkForwardRequest, db: Session = Depends(get_db)):
    """Chronologically split eligible spread history and score a simple out-of-sample rule.

    The training segment sets a fixed entry threshold only; the holdout is evaluated strictly
    after the split. A signal at t is evaluated against t+1 spread change, with costs charged
    on each triggered observation as a conservative non-overlapping one-step experiment.
    """
    a, b, inverted, canonical_pair = _pair(request.pair)
    series = RelativeValueAnalyticsService(db).calculate_pairwise_spread_series(
        leg_a=a, leg_b=b, window_days=request.window, invert_spread=inverted
    )
    points = [p for p in series.data_points if p.spread is not None and p.z_score is not None]
    if len(points) < max(request.window + 10, 30):
        raise HTTPException(status_code=422, detail=f"Insufficient eligible history: need at least {max(request.window + 10, 30)} usable points; found {len(points)}.")
    split = int(len(points) * request.train_fraction)
    if split < request.window or len(points) - split < 10:
        raise HTTPException(status_code=422, detail="The chronological split leaves too few training or holdout observations.")
    train, test = points[:split], points[split:]
    # Select the threshold from training-only absolute z-scores, but treat the
    # user-entered entry_z as a minimum. The UI parameter must never be silently ignored.
    threshold = _select_training_threshold([p.z_score for p in train], request.entry_z)
    cost_per_roundtrip = (request.transaction_cost_per_10g + request.slippage_per_10g) * 2 * request.units
    outcomes = []
    for idx in range(len(test) - 1):
        current, nxt = test[idx], test[idx + 1]
        z = current.z_score
        if z is None or abs(z) < threshold:
            continue
        # Mean-reversion direction based only on the signal known at current observation.
        direction = -1.0 if z > 0 else 1.0
        gross = (nxt.spread - current.spread) * direction * request.units
        outcomes.append({"date": str(current.trade_date), "next_date": str(nxt.trade_date),
                         "z_score": round(z, 4), "gross_pnl": round(gross, 2),
                         "estimated_costs": round(cost_per_roundtrip, 2),
                         "net_pnl": round(gross - cost_per_roundtrip, 2)})
    gross_total = sum(x["gross_pnl"] for x in outcomes)
    net_total = sum(x["net_pnl"] for x in outcomes)
    wins = sum(1 for x in outcomes if x["net_pnl"] > 0)
    return StandardResponse(success=True, message="Chronological historical validation completed; holdout outcomes are hypothetical settlement-to-settlement estimates.", data={
        "pair": canonical_pair, "status": "completed", "data_mode": "historical_csv_not_provider_verified",
        "observations": len(points), "training_observations": len(train), "holdout_observations": len(test),
        "training_start": train[0].trade_date, "training_end": train[-1].trade_date,
        "holdout_start": test[0].trade_date, "holdout_end": test[-1].trade_date,
        "train_fraction": request.train_fraction, "entry_threshold_selected_from_training": round(threshold, 4),
        "holdout_signal_count": len(outcomes), "gross_pnl": round(gross_total, 2),
        "estimated_costs": round(cost_per_roundtrip * len(outcomes), 2), "net_pnl": round(net_total, 2),
        "win_rate_pct": round(wins / len(outcomes) * 100, 2) if outcomes else None,
        "holdout_outcomes": outcomes,
        "assumptions": [
            "Rolling Z-scores are computed causally from trailing history; no future observation is used to form a signal.",
            "The training-only 90th-percentile threshold is bounded by the user-configured entry Z minimum; holdout outcomes do not influence threshold selection.",
            "Each signal is evaluated over the next synchronized observation, not a portfolio-level position simulator.",
            "Settlement prices are proxies, not executable quotes. Costs are estimates and actual contract/margin/tax effects may differ.",
            "Historical performance is not a guarantee of future results."
        ]
    })
