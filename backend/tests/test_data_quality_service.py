from datetime import date

from backend.app.models.market_observation import MarketObservation
from backend.app.services.data_quality_service import DataQualityService


def _observation(symbol, trade_day, expiry, *, source="csv_upload", synthetic=False,
                volume=0, volume_observed=False, oi=0, oi_observed=False):
    price = 62500.0
    return MarketObservation(
        symbol=symbol,
        trade_date=trade_day,
        expiry_date=expiry,
        close_price=price,
        normalized_price_per_gram=price / 10,
        normalized_price_10g_basis=price,
        volume=volume,
        volume_observed=volume_observed,
        open_interest=oi,
        open_interest_observed=oi_observed,
        data_source=source,
        is_synthetic=synthetic,
    )


def test_data_quality_uses_shared_provenance_and_exact_date_expiry_keys_read_only(db_session):
    day = date(2026, 10, 21)
    expiry = date(2026, 10, 30)
    db_session.add_all([
        _observation("GOLDM", day, expiry, volume=0, volume_observed=True,
                     oi=12, oi_observed=True),
        _observation("GOLDPETAL", day, expiry, volume=5, volume_observed=True,
                     oi=0, oi_observed=True),
        # Same session, different expiry must not count as a synchronized pair.
        _observation("GOLDTEN", day, date(2026, 11, 30)),
        _observation("GOLDGUINEA", day, expiry, source="synthetic_seed", synthetic=True,
                     volume=9, volume_observed=True),
    ])
    db_session.commit()
    before = db_session.query(MarketObservation).count()

    report = DataQualityService(db_session).report()

    assert report["stored_observation_count"] == 4
    assert report["eligible_observation_count"] == 3
    assert report["excluded_by_eligibility_count"] == 1
    assert report["exact_trade_date_and_expiry_pair_counts"]["GOLDM-GOLDPETAL"] == 1
    assert report["exact_trade_date_and_expiry_pair_counts"]["GOLDM-GOLDTEN"] == 0
    assert report["symbols"]["GOLDM"]["observed_zero_volume_count"] == 1
    assert report["symbols"]["GOLDM"]["missing_volume_observation_count"] == 0
    assert report["symbols"]["GOLDTEN"]["missing_volume_observation_count"] == 1
    assert report["bid_ask_observation_count"] == 0
    assert report["provider_verified_observation_count"] == 0
    assert db_session.query(MarketObservation).count() == before
