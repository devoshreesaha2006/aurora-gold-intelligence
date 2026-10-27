"""Regression tests for historical what-if holding horizons versus expiry."""

from datetime import date

from backend.app.api.intelligence import _scenario_horizon_warnings


def test_flags_historical_contract_already_expired_on_evaluation_date():
    warnings = _scenario_horizon_warnings(
        date(2024, 10, 31), date(2024, 10, 31), holding_days=5
    )
    assert any("based on an expired contract" in warning for warning in warnings)
    assert any("does not model expiry settlement" in warning for warning in warnings)


def test_flags_holding_horizon_that_reaches_expiry():
    warnings = _scenario_horizon_warnings(
        date(2024, 10, 27), date(2024, 10, 31), holding_days=5
    )
    assert len(warnings) == 1
    assert "on or after contract expiry" in warnings[0]


def test_does_not_warn_when_holding_horizon_ends_before_expiry():
    warnings = _scenario_horizon_warnings(
        date(2024, 10, 20), date(2024, 11, 30), holding_days=5
    )
    assert warnings == []


def test_warns_when_expiry_is_unavailable():
    warnings = _scenario_horizon_warnings(
        date(2024, 10, 20), None, holding_days=5
    )
    assert len(warnings) == 1
    assert "cannot be checked against expiry" in warnings[0]
