"""Regression tests for training-only walk-forward threshold selection."""

import pytest

from backend.app.api.intelligence import _select_training_threshold


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
