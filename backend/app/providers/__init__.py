from backend.app.providers.base import MarketDataProvider
from backend.app.providers.static_provider import StaticDatabaseProvider
from backend.app.providers.live_mock import AuthorizedMCXLiveProvider
from backend.app.config import settings
from threading import Lock

_live_provider = None
_live_provider_config = None
_live_provider_lock = Lock()


def get_market_provider() -> MarketDataProvider:
    """
    Factory function returning the configured MarketDataProvider.
    Defaults to StaticDatabaseProvider for reliable, zero-config local operation.
    """
    if settings.data_mode == "live_feed_authorized":
        global _live_provider, _live_provider_config
        key = (
            settings.mcx_feed_api_key, settings.mcx_feed_api_secret,
            settings.mcx_feed_base_url, settings.mcx_feed_provider_name,
            settings.mcx_feed_quotes_path, settings.mcx_feed_license_confirmed,
            settings.mcx_feed_timeout_seconds, settings.mcx_feed_live_max_age_seconds,
            settings.mcx_feed_delayed_max_age_seconds, settings.mcx_feed_poll_interval_seconds,
        )
        with _live_provider_lock:
            if _live_provider is None or _live_provider_config != key:
                if _live_provider is not None:
                    _live_provider.close()
                _live_provider = AuthorizedMCXLiveProvider()
                _live_provider_config = key
            return _live_provider
    return StaticDatabaseProvider()


__all__ = ["MarketDataProvider", "StaticDatabaseProvider", "AuthorizedMCXLiveProvider", "get_market_provider"]
