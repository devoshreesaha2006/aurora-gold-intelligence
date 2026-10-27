from datetime import date
from types import SimpleNamespace

import numpy as np

from backend.app.api.ml_research import features, select_front_expiry_history


def test_ml_features_work_at_first_valid_lag():
    prices = np.linspace(100.0, 112.0, 80)
    values = features(prices, 10)

    assert len(values) == 9
    assert all(np.isfinite(value) for value in values)


def test_ml_features_use_only_the_trailing_twenty_prices():
    prices = np.linspace(100.0, 150.0, 80)
    changed_history = prices.copy()
    changed_history[:51] *= 3

    # At index 70, the feature window starts at index 51. Earlier values must
    # not affect the feature vector.
    assert features(prices, 70) == features(changed_history, 70)


def test_ml_feature_vector_has_expected_lag_and_rolling_statistics():
    prices = np.array([100.0 + i * 0.7 + (i % 4) * 0.15 for i in range(40)])
    values = features(prices, 25)

    assert len(values) == 9
    assert all(np.isfinite(value) for value in values)
    assert values[0] == prices[25] / prices[24] - 1
    assert values[4] == prices[25] / prices[15] - 1



def test_front_expiry_history_selects_nearest_expiry_per_trade_date():
    rows = [
        SimpleNamespace(trade_date=date(2026, 10, 2), expiry_date=date(2026, 11, 30),
                        normalized_price_10g_basis=102.0),
        SimpleNamespace(trade_date=date(2026, 10, 1), expiry_date=date(2026, 11, 30),
                        normalized_price_10g_basis=100.0),
        SimpleNamespace(trade_date=date(2026, 10, 1), expiry_date=date(2026, 10, 30),
                        normalized_price_10g_basis=99.0),
        SimpleNamespace(trade_date=date(2026, 10, 2), expiry_date=date(2026, 10, 30),
                        normalized_price_10g_basis=101.0),
    ]

    history = select_front_expiry_history(rows)

    assert history == [
        (date(2026, 10, 1), 99.0, date(2026, 10, 30)),
        (date(2026, 10, 2), 101.0, date(2026, 10, 30)),
    ]


def test_front_expiry_history_ignores_non_positive_and_non_finite_prices():
    rows = [
        SimpleNamespace(trade_date=date(2026, 10, 1), expiry_date=date(2026, 10, 30),
                        normalized_price_10g_basis=float("nan")),
        SimpleNamespace(trade_date=date(2026, 10, 2), expiry_date=date(2026, 10, 30),
                        normalized_price_10g_basis=0.0),
        SimpleNamespace(trade_date=date(2026, 10, 3), expiry_date=date(2026, 10, 30),
                        normalized_price_10g_basis=105.0),
    ]

    history = select_front_expiry_history(rows)

    assert history == [(date(2026, 10, 3), 105.0, date(2026, 10, 30))]
