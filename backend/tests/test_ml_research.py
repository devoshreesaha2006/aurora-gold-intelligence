import numpy as np

from backend.app.api.ml_research import features


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
