from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import json

import httpx

from backend.app.models.market_observation import MarketObservation
from backend.app.providers.live_mock import AuthorizedMCXLiveProvider


def _quote(*, symbol="GOLDM", timestamp=None, expiry="2026-12-28", **overrides):
    timestamp_value = timestamp if isinstance(timestamp, str) else (timestamp or datetime.now(timezone.utc)).isoformat()
    payload = {
        "exchange": "MCX",
        "symbol": symbol,
        "expiry_date": expiry,
        "timestamp": timestamp_value,
        "last_price": 62500.0,
        "open_price": 62400.0,
        "high_price": 62600.0,
        "low_price": 62300.0,
        "volume": 120,
        "open_interest": 450,
    }
    payload.update(overrides)
    return payload


def _provider(handler, **kwargs):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return AuthorizedMCXLiveProvider(
        api_key="test-key",
        api_secret="test-secret",
        base_url="https://feed.example.test/api",
        provider_name="Test Authorized Distributor",
        license_confirmed=True,
        poll_interval_seconds=0,
        http_client=client,
        **kwargs,
    )


def _ok_body(*quotes, feed_type="live"):
    return {"authenticated": True, "exchange": "MCX", "feed_type": feed_type, "observations": list(quotes)}


def test_live_provider_requires_authenticated_mcxtimestamped_persisted_quotes(db_session):
    seen_headers = {}

    def handler(request):
        seen_headers.update(request.headers)
        return httpx.Response(200, json=_ok_body(_quote()))

    provider = _provider(handler)
    assert provider.poll_once(db_session, force=True) == 1
    status = provider.get_market_status(db_session)

    row = db_session.query(MarketObservation).one()
    assert row.is_provider_verified is True
    assert row.is_synthetic is False
    assert row.data_source.startswith("authorized_provider:")
    assert row.data_source.endswith(":live")
    assert row.provider_timestamp is not None
    assert row.normalized_price_10g_basis > 0
    assert status.feed_status == "LIVE"
    assert status.authentication_state == "authenticated"
    assert status.is_live_connected is True
    assert status.total_observations == 1
    assert seen_headers["x-api-key"] == "test-key"
    assert seen_headers["x-api-secret"] == "test-secret"


def test_provider_authentication_failure_is_unavailable(db_session):
    def handler(request):
        return httpx.Response(401, json={"error": "bad credentials"})

    provider = _provider(handler)
    status = provider.get_market_status(db_session)
    assert status.feed_status == "UNAVAILABLE"
    assert status.authentication_state == "failed"
    assert status.is_live_connected is False
    assert db_session.query(MarketObservation).count() == 0


def test_provider_timeout_is_disconnected_without_data(db_session):
    def handler(request):
        raise httpx.ReadTimeout("simulated timeout", request=request)

    provider = _provider(handler)
    status = provider.get_market_status(db_session)
    assert status.feed_status == "UNAVAILABLE"
    assert status.connection_state == "disconnected"
    assert status.provider_error == "Provider request timed out"
    assert db_session.query(MarketObservation).count() == 0


def test_provider_rejects_malformed_quote_and_unknown_instrument(db_session):
    for quote in (_quote(last_price="not-a-price"), _quote(symbol="SILVER")):
        provider = _provider(lambda request, quote=quote: httpx.Response(200, json=_ok_body(quote)))
        assert provider.poll_once(db_session, force=True) == 0
        assert db_session.query(MarketObservation).count() == 0


def test_provider_rejects_naive_or_stale_timestamps(db_session):
    naive = datetime.now().replace(tzinfo=None).isoformat()
    old = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()

    provider = _provider(lambda request: httpx.Response(200, json=_ok_body(_quote(timestamp=naive))))
    assert provider.poll_once(db_session, force=True) == 0
    assert "timezone" in provider._provider_error

    provider = _provider(lambda request: httpx.Response(200, json=_ok_body(_quote(timestamp=old))))
    assert provider.poll_once(db_session, force=True) == 0
    status = provider.get_market_status(db_session)
    assert status.feed_status == "STALE"
    assert status.is_live_connected is False
    assert db_session.query(MarketObservation).count() == 0


def test_provider_delayed_feed_is_never_labelled_live(db_session):
    provider = _provider(lambda request: httpx.Response(200, json=_ok_body(
        _quote(), feed_type="delayed_5m"
    )))
    assert provider.poll_once(db_session, force=True) == 1
    status = provider.get_market_status(db_session)
    assert status.feed_status == "DELAYED"
    assert status.is_live_connected is False


def test_provider_duplicate_observations_are_idempotent_and_never_replace_csv(db_session):
    quote = _quote()
    provider = _provider(lambda request: httpx.Response(200, json=_ok_body(quote)))
    assert provider.poll_once(db_session, force=True) == 1
    assert provider.poll_once(db_session, force=True) == 1
    assert db_session.query(MarketObservation).count() == 1

    provider_quote = _quote(symbol="GOLDTEN")
    csv_row = MarketObservation(
        symbol="GOLDTEN", trade_date=datetime.fromisoformat(provider_quote["timestamp"]).astimezone(ZoneInfo("Asia/Kolkata")).date(),
        expiry_date=datetime.fromisoformat(provider_quote["expiry_date"]).date(),
        close_price=62000, normalized_price_per_gram=6200,
        normalized_price_10g_basis=62000, data_source="csv_upload",
    )
    db_session.add(csv_row)
    db_session.commit()
    provider2 = _provider(lambda request: httpx.Response(200, json=_ok_body(provider_quote)))
    assert provider2.poll_once(db_session, force=True) == 0
    assert db_session.query(MarketObservation).filter_by(symbol="GOLDTEN").one().data_source == "csv_upload"


def test_configured_credentials_without_license_attestation_do_not_connect(db_session):
    provider = AuthorizedMCXLiveProvider(
        api_key="key", api_secret="secret", base_url="https://feed.example.test",
        license_confirmed=False,
    )
    assert provider.poll_once(db_session, force=True) == 0
    status = provider.get_market_status(db_session)
    assert status.feed_status == "UNAVAILABLE"
    assert status.is_live_connected is False
    assert status.authentication_state == "unknown"


def test_missing_provider_configuration_stays_unavailable_without_request(db_session):
    requests = []
    client = httpx.Client(transport=httpx.MockTransport(
        lambda request: (requests.append(request), httpx.Response(200, json=_ok_body(_quote())))[1]
    ))
    provider = AuthorizedMCXLiveProvider(
        api_key="", api_secret="", base_url="",
        license_confirmed=True, http_client=client,
    )

    status = provider.get_market_status(db_session)

    assert status.feed_status == "UNAVAILABLE"
    assert status.connection_state == "disconnected"
    assert status.authentication_state == "unknown"
    assert status.is_live_connected is False
    assert requests == []
    assert db_session.query(MarketObservation).count() == 0


def test_authenticated_provider_with_no_observations_is_unavailable(db_session):
    provider = _provider(lambda request: httpx.Response(200, json={
        "authenticated": True,
        "exchange": "MCX",
        "feed_type": "live",
        "observations": [],
    }))

    status = provider.get_market_status(db_session)

    assert status.feed_status == "UNAVAILABLE"
    assert status.connection_state == "connected"
    assert status.authentication_state == "authenticated"
    assert status.is_live_connected is False
    assert status.total_observations == 0
    assert status.last_provider_timestamp is None
    assert status.market_open is None
    assert status.market_session_status == "unknown"
    assert db_session.query(MarketObservation).count() == 0


def test_provider_status_ignores_unverified_rows_even_with_provider_like_source(db_session):
    db_session.add(MarketObservation(
        symbol="GOLDM", trade_date=datetime.now(timezone.utc).date(), expiry_date=datetime(2026, 12, 28).date(),
        close_price=62500, normalized_price_per_gram=6250,
        normalized_price_10g_basis=62500, data_source="authorized_provider:forged:live",
        is_synthetic=False, is_provider_verified=False,
    ))
    db_session.commit()

    provider = AuthorizedMCXLiveProvider(license_confirmed=False)
    status = provider.get_market_status(db_session)
    assert status.total_observations == 0
    assert status.feed_status == "UNAVAILABLE"
