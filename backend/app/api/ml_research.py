import math
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.market_observation import MarketObservation
from backend.app.services.data_provenance import eligible_analytics_observations_query

router = APIRouter(prefix="/research", tags=["Research, Forecasting & Risk"])
SYMBOL_PATTERN = "^(GOLDM|GOLDTEN|GOLDGUINEA|GOLDPETAL)$"


def features(prices, i):
    """Build causal features using only the last 20 prices (linear overall work)."""
    # All features use at most 20 prices. Slicing the entire prefix and diffing it
    # for every row made feature generation quadratic and could stall the request.
    p = np.asarray(prices[max(0, i - 19):i + 1], dtype=float)
    r = np.diff(p) / p[:-1]
    return [p[-1] / p[-1 - k] - 1 for k in (1, 2, 3, 5, 10)] + [
        float(np.std(r[-5:], ddof=1)), float(np.std(r[-10:], ddof=1)),
        float(p[-1] / np.mean(p[-5:]) - 1), float(p[-1] / np.mean(p[-20:]) - 1)
    ]


@router.get("/ml-spread-forecast")
def ml_spread_forecast(symbol: str = Query("GOLDM", pattern=SYMBOL_PATTERN),
                       max_folds: int = Query(10, ge=5, le=30),
                       db: Session = Depends(get_db)):
    """Experimental Random Forest forecast with chronological out-of-sample evaluation."""
    try:
        from sklearn.ensemble import RandomForestRegressor
    except ImportError:
        raise HTTPException(status_code=503, detail="Install requirements.txt and restart FastAPI.")
    rows = (eligible_analytics_observations_query(db)
            .filter(MarketObservation.symbol == symbol)
            .order_by(MarketObservation.trade_date.asc(), MarketObservation.expiry_date.asc()).all())
    by_date = {}
    for row in rows:
        by_date.setdefault(row.trade_date, row)
    hist = [(day, float(row.normalized_price_10g_basis)) for day, row in sorted(by_date.items())
            if row.normalized_price_10g_basis is not None
            and math.isfinite(float(row.normalized_price_10g_basis))
            and float(row.normalized_price_10g_basis) > 0]
    p = np.asarray([v for _, v in hist], dtype=float)
    if len(p) < 60:
        return {"status": "insufficient_history", "symbol": symbol, "observations": len(p),
                "minimum_required": 60, "metrics": None, "folds": [],
                "message": "At least 60 eligible historical dates are required; no synthetic data is used."}

    def new_model():
        return RandomForestRegressor(n_estimators=30, max_depth=4, min_samples_leaf=3,
                                     max_features=0.9, random_state=42, n_jobs=1)

    folds = []
    actual = []
    predicted = []
    naive = []
    # Features require at least 11 observations because the longest lag is 10.
    # Avoid computing invalid features for the first 10 positions.
    feature_cache = [None] * 10 + [features(p, j) for j in range(10, len(p))]
    target_returns = [float(p[j + 1] / p[j] - 1) for j in range(len(p) - 1)]
    for i in range(max(40, len(p) - max_folds - 1), len(p) - 1):
        x = feature_cache[10:i]
        y = target_returns[10:i]
        if len(x) < 30:
            continue
        model = new_model()
        model.fit(np.asarray(x), np.asarray(y))
        pred = float(model.predict(np.asarray([feature_cache[i]]))[0])
        act = float(target_returns[i])
        actual.append(act)
        predicted.append(pred)
        naive.append(0.0)
        origin_price = float(p[i])
        actual_price = float(p[i + 1])
        folds.append({
            "origin_date": hist[i][0].isoformat(),
            "target_date": hist[i + 1][0].isoformat(),
            "origin_price_10g": round(origin_price, 2),
            "actual_price_10g": round(actual_price, 2),
            "ml_predicted_price_10g": round(origin_price * (1 + pred), 2),
            "naive_predicted_price_10g": round(origin_price, 2),
            "actual_change_pct": round(act * 100, 5),
            "ml_predicted_change_pct": round(pred * 100, 5),
            "naive_predicted_change_pct": 0.0,
            "absolute_error_pct_points": round(abs(act - pred) * 100, 6),
            "naive_absolute_error_pct_points": round(abs(act) * 100, 6),
            "direction_correct": bool(np.sign(act) == np.sign(pred)) if act != 0 else None,
            "training_targets": len(x),
        })
    if not folds:
        return {"status": "insufficient_history", "symbol": symbol, "observations": len(p),
                "metrics": None, "folds": []}

    def metrics(a, b):
        a = np.asarray(a)
        b = np.asarray(b)
        mask = a != 0
        return {"mae_change_pct_points": round(float(np.mean(np.abs(a - b) * 100)), 6),
                "rmse_change_pct_points": round(float(np.sqrt(np.mean(((a - b) * 100) ** 2))), 6),
                "directional_accuracy_pct": round(float(np.mean(np.sign(a[mask]) == np.sign(b[mask])) * 100), 2)
                if np.any(mask) else None}

    mm = metrics(actual, predicted)
    nm = metrics(actual, naive)
    x = feature_cache[10:len(p) - 1]
    y = target_returns[10:len(p) - 1]
    model = new_model()
    model.fit(np.asarray(x), np.asarray(y))
    change = float(model.predict(np.asarray([feature_cache[len(p) - 1]]))[0])
    return {"status": "evaluated", "model": "RandomForestRegressor", "symbol": symbol,
            "basis": "₹ per 10g, 995 fine-gold benchmark", "observations": len(p), "test_folds": len(folds),
            "first_test_date": folds[0]["target_date"], "last_test_date": folds[-1]["target_date"],
            "latest_observation_date": hist[-1][0].isoformat(), "latest_price_10g": round(float(p[-1]), 2),
            "next_observation_experimental_change_pct": round(change * 100, 5),
            "next_observation_experimental_price_10g": round(float(p[-1] * (1 + change)), 2),
            "metrics": {"random_forest": mm, "naive_zero_change": nm},
            "comparison": {"ml_lower_mae_than_naive": mm["mae_change_pct_points"] < nm["mae_change_pct_points"]},
            "folds": folds,
            "method": "Expanding chronological training; lagged returns and rolling statistics use only prior data.",
            "caveat": "Experimental research only, not a live quote or trading signal. Imported history may not be exchange-verified; future performance is unknown."}
