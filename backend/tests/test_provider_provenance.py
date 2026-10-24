from datetime import date

from backend.app.models.market_observation import MarketObservation
from backend.app.providers.live_mock import AuthorizedMCXLiveProvider
from backend.app.providers.static_provider import StaticDatabaseProvider
from backend.app.providers import get_market_provider
from backend.app.providers import settings as provider_settings


def _observation(day, source, *, synthetic=False):
    return MarketObservation(
        symbol="GOLDM", trade_date=day, expiry_date=date(2026, 12, 28),
        close_price=62500, normalized_price_per_gram=6250,
        normalized_price_10g_basis=62500, volume=1, open_interest=1,
        data_source=source, is_synthetic=synthetic,
    )


def test_api_key_and_url_do_not_claim_live_connection(db_session):
    provider = AuthorizedMCXLiveProvider(
        api_key="a-long-configured-api-key", api_secret="configured-secret",
        base_url="https://provider.example/api",
    )

    status = provider.get_market_status(db_session)
    assert provider.is_live_connected() is False
    assert status.is_live_connected is False
    assert status.feed_status == "UNAVAILABLE"
    assert status.data_mode == "live_feed_disconnected"
    assert status.total_observations == 0
    assert status.feed_status == "UNAVAILABLE"
    assert status.authentication_state == "unknown"
    assert "license confirmation" in status.provider_error.lower()
    assert status.market_open is None
    assert status.market_session_status == "unknown"


def test_configured_live_mode_stays_on_disconnected_adapter_without_credentials(monkeypatch):
    monkeypatch.setattr(provider_settings, "data_mode", "live_feed_authorized")
    monkeypatch.setattr(provider_settings, "mcx_feed_api_key", None)

    provider = get_market_provider()
    assert isinstance(provider, AuthorizedMCXLiveProvider)
    assert provider.is_live_connected() is False


def test_static_status_distinguishes_imported_csv_synthetic_and_test_rows(db_session):
    db_session.add_all([
        _observation(date(2026, 10, 1), "csv_upload"),
        _observation(date(2026, 10, 2), "synthetic_seed", synthetic=True),
        _observation(date(2026, 10, 3), "test_invalid"),
    ])
    db_session.commit()

    status = StaticDatabaseProvider().get_market_status(db_session)
    assert status.data_mode == "staged_csv"
    assert "User-imported historical CSV (not provider-verified)" in status.data_freshness_label
    assert "Synthetic data present" in status.data_freshness_label
    assert "Test data present" in status.data_freshness_label
    assert "No verified provider observations" in status.data_freshness_label
    assert "Historical Bhavcopy" not in status.data_freshness_label
    assert status.is_live_connected is False
    assert status.market_open is None
    assert status.market_session_status == "unknown"


def test_test_only_observations_are_not_reported_as_csv_history(db_session):
    db_session.add(_observation(date(2026, 10, 1), "test_run"))
    db_session.commit()

    status = StaticDatabaseProvider().get_market_status(db_session)
    assert status.data_mode == "test_data"
    assert "Test data present" in status.data_freshness_label
    assert "Bhavcopy" not in status.data_freshness_label
