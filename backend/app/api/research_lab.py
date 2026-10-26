"""Research endpoints for historical forecasting, risk sizing, and data exports.

All outputs are derived from stored eligible observations or explicit user inputs.
No external/live data is fabricated by this module.
"""
import csv
import io
import math
from datetime import date
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.market_observation import MarketObservation
from backend.app.services.data_provenance import eligible_analytics_observations_query

router = APIRouter(prefix="/research", tags=["Research, Forecasting & Risk"])


class RiskSizingRequest(BaseModel):
    capital: float = Field(gt=0, le=1_000_000_000)
    risk_pct: float = Field(default=1.0, gt=0, le=10)
    entry_price: float = Field(gt=0)
    stop_price: float = Field(gt=0)
    unit_size: float = Field(default=1.0, gt=0)
    estimated_cost_per_unit: float = Field(default=0, ge=0)


@router.get("/forecast")
def historical_forecast(
    symbol: str = Query("GOLDM", pattern="^(GOLDM|GOLDTEN|GOLDGUINEA|GOLDPETAL)$"),
    horizon: int = Query(5, ge=1, le=20),
    lookback: int = Query(60, ge=10, le=1000),
    db: Session = Depends(get_db),
):
    """A simple transparent linear-trend baseline, not a validated trading signal."""
    rows = (
        eligible_analytics_observations_query(db)
        .filter(MarketObservation.symbol == symbol)
        .order_by(MarketObservation.trade_date.asc(), MarketObservation.expiry_date.asc())
        .all()
    )
    # Collapse multiple expiries to one nearest available observation per date.
    by_date = {}
    for row in rows:
        by_date.setdefault(row.trade_date, row)
    history = [(day, row.normalized_price_10g_basis) for day, row in sorted(by_date.items())]
    history = [(day, float(price)) for day, price in history if price is not None and math.isfinite(float(price))]
    history = history[-lookback:]
    if len(history) < 10:
        return {
            "status": "insufficient_history", "symbol": symbol, "observations": len(history),
            "message": "At least 10 eligible historical dates are required. Import eligible historical data first.",
            "forecast": [], "metrics": None,
            "caveat": "This endpoint never substitutes synthetic/demo observations for eligible history.",
        }
    y = np.array([price for _, price in history], dtype=float)
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    fitted = intercept + slope * x
    residual = y - fitted
    rmse = float(np.sqrt(np.mean(residual ** 2)))
    last = float(y[-1])
    forecasts = []
    for step in range(1, horizon + 1):
        predicted = float(intercept + slope * (len(y) - 1 + step))
        # Descriptive residual band only; not a calibrated prediction interval.
        forecasts.append({
            "step": step,
            "baseline_price_10g": round(predicted, 2),
            "baseline_change_pct": round((predicted / last - 1) * 100, 4) if last else None,
            "descriptive_lower": round(predicted - 1.96 * rmse, 2),
            "descriptive_upper": round(predicted + 1.96 * rmse, 2),
        })
    return {
        "status": "baseline_only", "symbol": symbol, "basis": "₹ per 10g, 995 fine-gold benchmark",
        "last_observation_date": history[-1][0].isoformat(), "observations": len(history),
        "last_price_10g": round(last, 2), "forecast": forecasts,
        "metrics": {"trend_slope_per_observation": round(float(slope), 6), "in_sample_rmse": round(rmse, 2)},
        "caveat": "Linear-trend research baseline only; not a trained production ML model, calibrated interval, probability of profit, or investment recommendation.",
    }


@router.post("/risk-sizing")
def risk_sizing(request: RiskSizingRequest):
    """Position-sizing arithmetic based on explicit user-supplied assumptions."""
    distance = abs(request.entry_price - request.stop_price)
    if distance <= 0:
        raise HTTPException(status_code=422, detail="Entry and stop prices must differ.")
    risk_budget = request.capital * request.risk_pct / 100
    per_unit_risk = distance * request.unit_size + request.estimated_cost_per_unit
    if per_unit_risk <= 0:
        raise HTTPException(status_code=422, detail="Estimated risk per unit must be positive.")
    units = math.floor(risk_budget / per_unit_risk)
    return {
        "capital": request.capital, "risk_pct": request.risk_pct, "risk_budget": round(risk_budget, 2),
        "price_distance": round(distance, 6), "estimated_risk_per_unit": round(per_unit_risk, 2),
        "max_units_by_input_assumptions": units, "estimated_total_risk": round(units * per_unit_risk, 2),
        "remaining_risk_budget": round(risk_budget - units * per_unit_risk, 2),
        "warning": "Arithmetic illustration only. It excludes margin, liquidity, gaps, contract lot rules, taxes not included in your cost input, and execution risk. Validate actual contract specifications before trading.",
    }


@router.get("/macro-context")
def macro_context():
    """Explicitly declare unconfigured external context rather than invent values."""
    return {
        "status": "not_configured",
        "items": [
            {"name": "International gold (USD/oz)", "status": "unavailable", "value": None, "source": None},
            {"name": "USD/INR", "status": "unavailable", "value": None, "source": None},
            {"name": "US real yields / rates", "status": "unavailable", "value": None, "source": None},
            {"name": "Cross-asset ratios", "status": "unavailable", "value": None, "source": None},
            {"name": "News sentiment", "status": "unavailable", "value": None, "source": None},
        ],
        "message": "No verified external macro/news provider is configured. Values and sentiment are intentionally left unavailable.",
    }


@router.get("/event-calendar")
def event_calendar():
    """No fake upcoming dates: a licensed or user-maintained calendar is required."""
    return {
        "status": "not_configured", "events": [],
        "message": "Economic calendar is not connected. Add a verified calendar source before showing event dates or impact labels.",
    }


@router.get("/export-observations")
def export_observations(
    symbol: Optional[str] = Query(None, pattern="^(GOLDM|GOLDTEN|GOLDGUINEA|GOLDPETAL)$"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(10000, ge=1, le=50000),
    db: Session = Depends(get_db),
):
    """Download eligible historical observations as CSV."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date.")
    query = eligible_analytics_observations_query(db)
    if symbol:
        query = query.filter(MarketObservation.symbol == symbol)
    if start_date:
        query = query.filter(MarketObservation.trade_date >= start_date)
    if end_date:
        query = query.filter(MarketObservation.trade_date <= end_date)
    rows = query.order_by(MarketObservation.trade_date.asc(), MarketObservation.symbol.asc(), MarketObservation.expiry_date.asc()).limit(limit).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["trade_date", "symbol", "expiry_date", "quoted_price", "normalized_price_per_gram", "normalized_price_10g_basis", "volume", "open_interest", "data_source", "provider_verified"])
    for row in rows:
        writer.writerow([
            row.trade_date, row.symbol, row.expiry_date, row.close_price,
            row.normalized_price_per_gram, row.normalized_price_10g_basis,
            row.volume, row.open_interest, row.data_source,
            getattr(row, "is_provider_verified", False),
        ])
    output.seek(0)
    filename = f"aurora_observations_{symbol or 'all'}.csv"
    return StreamingResponse(
        iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@router.get("/forecast-validation")
def forecast_validation(
    symbol: str = Query("GOLDM", pattern="^(GOLDM|GOLDTEN|GOLDGUINEA|GOLDPETAL)$"),
    lookback: int = Query(60, ge=20, le=500, description="Maximum prior observations used per fold"),
    min_train: int = Query(30, ge=20, le=500, description="Minimum chronological training observations"),
    max_folds: int = Query(120, ge=10, le=250, description="Maximum most-recent one-step test folds"),
    db: Session = Depends(get_db),
):
    """Compare naive, rolling-mean, and linear-trend forecasts with chronological folds."""
    rows = (
        eligible_analytics_observations_query(db)
        .filter(MarketObservation.symbol == symbol)
        .order_by(MarketObservation.trade_date.asc(), MarketObservation.expiry_date.asc())
        .all()
    )
    # Keep one eligible observation per date, consistently choosing the first expiry
    # under the deterministic expiry ordering above.
    by_date = {}
    for row in rows:
        by_date.setdefault(row.trade_date, row)
    history = [
        (day, float(row.normalized_price_10g_basis))
        for day, row in sorted(by_date.items())
        if row.normalized_price_10g_basis is not None
        and math.isfinite(float(row.normalized_price_10g_basis))
        and float(row.normalized_price_10g_basis) > 0
    ]
    if len(history) < min_train + 10:
        return {
            "status": "insufficient_history",
            "symbol": symbol,
            "observations": len(history),
            "minimum_required": min_train + 10,
            "metrics": None,
            "folds": [],
            "message": "Not enough eligible distinct dates for chronological out-of-sample validation. Import more eligible history.",
        }

    first_test = max(min_train, len(history) - max_folds)
    folds = []
    actuals, naive_predictions, mean_predictions, trend_predictions = [], [], [], []
    for test_index in range(first_test, len(history)):
        train_start = max(0, test_index - lookback)
        train = history[train_start:test_index]
        if len(train) < min_train:
            continue
        train_y = np.array([price for _, price in train], dtype=float)
        x_train = np.arange(len(train_y), dtype=float)
        slope, intercept = np.polyfit(x_train, train_y, 1)
        actual = float(history[test_index][1])
        previous = float(train_y[-1])
        naive = previous
        rolling_mean = float(np.mean(train_y[-min(5, len(train_y)):]))
        trend = float(intercept + slope * len(train_y))
        actuals.append(actual)
        naive_predictions.append(naive)
        mean_predictions.append(rolling_mean)
        trend_predictions.append(trend)
        folds.append({
            "date": history[test_index][0].isoformat(),
            "actual_price_10g": round(actual, 2),
            "previous_price_10g": round(previous, 2),
            "naive_prediction_10g": round(naive, 2),
            "rolling_mean_prediction_10g": round(rolling_mean, 2),
            "trend_prediction_10g": round(trend, 2),
            "naive_absolute_error": round(abs(actual - naive), 2),
            "rolling_mean_absolute_error": round(abs(actual - rolling_mean), 2),
            "trend_absolute_error": round(abs(actual - trend), 2),
            "training_observations": len(train),
        })

    def metric_pack(actual_values, predicted_values):
        actual_arr = np.asarray(actual_values, dtype=float)
        predicted_arr = np.asarray(predicted_values, dtype=float)
        errors = predicted_arr - actual_arr
        return {
            "mae": round(float(np.mean(np.abs(errors))), 2),
            "rmse": round(float(np.sqrt(np.mean(errors ** 2))), 2),
            "mape_pct": round(float(np.mean(np.abs(errors / actual_arr)) * 100), 4),
        }

    naive_metrics = metric_pack(actuals, naive_predictions)
    mean_metrics = metric_pack(actuals, mean_predictions)
    trend_metrics = metric_pack(actuals, trend_predictions)
    previous_values = [float(history[max(0, first_test + i - 1)][1]) for i in range(len(actuals))]
    def direction_accuracy(predicted_values):
        correct = [((p - prev) > 0) == ((actual - prev) > 0) for p, prev, actual in zip(predicted_values, previous_values, actuals) if actual != prev]
        return round(sum(correct) / len(correct) * 100, 2) if correct else None
    naive_metrics["directional_accuracy_pct"] = direction_accuracy(naive_predictions)
    mean_metrics["directional_accuracy_pct"] = direction_accuracy(mean_predictions)
    trend_metrics["directional_accuracy_pct"] = direction_accuracy(trend_predictions)
    trend_wins = sum(abs(a - t) < abs(a - n) for a, t, n in zip(actuals, trend_predictions, naive_predictions))
    ties = sum(abs(a - t) == abs(a - n) for a, t, n in zip(actuals, trend_predictions, naive_predictions))
    best_model = min({"naive_last_value": naive_metrics, "rolling_mean_5": mean_metrics, "linear_trend": trend_metrics}, key=lambda name: {"naive_last_value": naive_metrics, "rolling_mean_5": mean_metrics, "linear_trend": trend_metrics}[name]["mae"])
    return {
        "status": "evaluated",
        "symbol": symbol,
        "basis": "₹ per 10g, 995 fine-gold benchmark",
        "observations": len(history),
        "test_folds": len(folds),
        "first_test_date": folds[0]["date"] if folds else None,
        "last_test_date": folds[-1]["date"] if folds else None,
        "method": "Chronological one-step walk-forward; each prediction uses only earlier eligible distinct dates; linear trend is refit at each fold.",
        "models": {
            "naive_last_value": naive_metrics,
            "rolling_mean_5": mean_metrics,
            "linear_trend": trend_metrics,
        },
        "selection": {"lowest_mae_model": best_model, "rule": "Descriptive winner among tested baselines on this evaluation window only; not a guarantee of future performance."},
        "comparison": {
            "trend_lower_mae_than_naive": trend_metrics["mae"] < naive_metrics["mae"],
            "trend_wins": trend_wins,
            "ties": ties,
            "trend_win_rate_pct": round(trend_wins / len(folds) * 100, 2) if folds else None,
        },
        "folds": folds,
        "caveat": "Historical out-of-sample error comparison only. Lowest MAE is descriptive and can vary by test window. Not a trading signal or evidence of future performance; imported data may not be exchange-verified. One-step validation does not validate multi-step forecasts.",
    }
