"""Regression tests for training-only walk-forward threshold selection."""

import pytest
from datetime import date, timedelta
from types import SimpleNamespace

from backend.app.api.intelligence import (
    WalkForwardRequest,
    _select_training_threshold,
    walk_forward_validation,
)
from backend.app.services.analytics_service import RelativeValueAnalyticsService


def test_user_entry_z_is_a_minimum_for_selected_training_threshold():
    # A lower training quantile must not silently override the UI's configured threshold.
    assert _select_training_threshold([1.0, 1.1, 1.2, 1.3, 1.48], 2.0) == pytest.approx(2.0)


def test_training_quantile_can_raise_threshold_above_user_minimum():
    scores = [0.4, 0.8, 1.0, 1.2, 1.48, 1.6, 1.8, 2.2, 2.6, 2.8]
    assert _select_training_threshold(scores, 1.0) == pytest.approx(2.6)


def test_empty_training_scores_fall_back_to_user_entry_z():
    assert _select_training_threshold([None, float("nan")], 1.75) == pytest.approx(1.75)


def test_training_threshold_is_capped_at_three_unless_user_sets_higher_floor():
    scores = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert _select_training_threshold(scores, 1.0) == pytest.approx(3.0)
    assert _select_training_threshold(scores, 4.0) == pytest.approx(4.0)


def test_walk_forward_excludes_pnl_transition_across_expiries(db_session, monkeypatch):
    first_day = date(2026, 1, 1)
    points = [
        SimpleNamespace(
            trade_date=first_day + timedelta(days=index),
            expiry_date=date(2027, 1, 28) if index < 33 else date(2027, 2, 25),
            spread=float(index),
            z_score=3.0,
        )
        for index in range(40)
    ]
    monkeypatch.setattr(
        RelativeValueAnalyticsService,
        "calculate_pairwise_spread_series",
        lambda *args, **kwargs: SimpleNamespace(data_points=points),
    )

    response = walk_forward_validation(WalkForwardRequest(**{
        "pair": "GOLDM-GOLDPETAL",
        "window": 5,
        "train_fraction": 0.7,
        "entry_z": 0.5,
        "transaction_cost_per_10g": 0,
        "slippage_per_10g": 0,
        "units": 1,
    }), db_session)

    result = response.data
    assert result["expiry_transition_exclusions"] == 1
    assert result["holdout_signal_count"] == 10
    assert all(outcome["expiry_date"] for outcome in result["holdout_outcomes"])
    assert all(
        points_by_date[outcome["date"]].expiry_date == points_by_date[outcome["next_date"]].expiry_date
        for outcome in result["holdout_outcomes"]
        for points_by_date in [{str(point.trade_date): point for point in points}]
    )
