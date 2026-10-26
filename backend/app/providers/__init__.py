from backend.app.providers.base import MarketDataProvider
from backend.app.providers.static_provider import StaticDatabaseProvider
from backend.app.providers.live_mock import AuthorizedMCXLiveProvider
from backend.app.providers.smartapi_provider import SmartAPIProvider
from backend.app.config import settings
from threading import Lock

_provider = None
_provider_config = None
_provider_lock = Lock()


def get_market_provider() -> MarketDataProvider:
    """Return a cached provider selected by explicit local configuration."""
    global _provider, _provider_config
    mode = (settings.data_mode or "").strip().lower()
    if mode == "smartapi":
        key = (
            mode, settings.smartapi_api_key, settings.smartapi_jwt_token,
            settings.smartapi_client_code, settings.smartapi_local_ip,
            settings.smartapi_public_ip, settings.smartapi_mac_address,
            settings.smartapi_mcx_token_map, settings.smartapi_license_confirmed,
            settings.smartapi_timeout_seconds, settings.smartapi_max_age_seconds,
            settings.smartapi_poll_interval_seconds,
        )
        with _provider_lock:
            if _provider is None or _provider_config != key:
                if _provider is not None and hasattr(_provider, "close"):
                    _provider.close()
                _provider = SmartAPIProvider()
                _provider_config = key
            return _provider
    if mode == "live_feed_authorized":
        key = (
            mode, settings.mcx_feed_api_key, settings.mcx_feed_api_secret,
            settings.mcx_feed_base_url, settings.mcx_feed_provider_name,
            settings.mcx_feed_quotes_path, settings.mcx_feed_license_confirmed,
            settings.mcx_feed_timeout_seconds, settings.mcx_feed_live_max_age_seconds,
            settings.mcx_feed_delayed_max_age_seconds, settings.mcx_feed_poll_interval_seconds,
        )
        with _provider_lock:
            if _provider is None or _provider_config != key:
                if _provider is not None and hasattr(_provider, "close"):
                    _provider.close()
                _provider = AuthorizedMCXLiveProvider()
                _provider_config = key
            return _provider
    return StaticDatabaseProvider()


__all__ = ["MarketDataProvider", "StaticDatabaseProvider", "AuthorizedMCXLiveProvider", "SmartAPIProvider", "get_market_provider"]
