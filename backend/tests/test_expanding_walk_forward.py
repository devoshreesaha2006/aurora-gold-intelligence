from datetime import date, timedelta
from types import SimpleNamespace

from backend.app.api.intelligence import ExpandingWalkForwardRequest, expanding_walk_forward_validation
from backend.app.services.analytics_service import RelativeValueAnalyticsService


def test_expanding_walk_forward_uses_chronological_folds_and_excludes_expiry_rolls(db_session, monkeypatch):
    points = []
    first_day = date(2026, 1, 1)
    for index in range(40):
        expiry = date(2027, 1, 28) if index < 27 else date(2027, 2, 25)
        points.append(SimpleNamespace(
            trade_date=first_day + timedelta(days=index),
            expiry_date=expiry,
            spread=float(index),
            z_score=3.0,
        ))

    monkeypatch.setattr(
        RelativeValueAnalyticsService,
        "calculate_pairwise_spread_series",
        lambda *args, **kwargs: SimpleNamespace(data_points=points),
    )

    result = expanding_walk_forward_validation(ExpandingWalkForwardRequest(**{
        "pair": "GOLDM-GOLDPETAL",
        "window": 5,
        "train_fraction": 0.6,
        "folds": 3,
        "entry_z": 0.5,
        "transaction_cost_per_10g": 10,
        "slippage_per_10g": 5,
        "units": 1,
    }), db_session)

    result = result.data
    assert result["status"] == "completed"
    assert result["data_mode"] == "historical_csv_not_provider_verified"
    assert result["training_observations"] == 24
    assert result["holdout_observations"] == 16
    assert [fold["training_observations"] for fold in result["folds"]] == [24, 30, 35]
    for fold in result["folds"]:
        assert fold["training_end"] < fold["testing_start"]
        assert fold["entry_threshold_selected_from_training"] == 3.0
    assert result["expiry_transition_exclusions"] == 1
    assert result["holdout_signal_count"] == 12
    assert all(
        point["date"] != "2026-01-27" and point["next_date"] != "2026-01-28"
        for point in result["holdout_outcomes"]
    )
    assert result["estimated_costs"] == 360
    assert any("not executable bid/ask fills" in item for item in result["assumptions"])
