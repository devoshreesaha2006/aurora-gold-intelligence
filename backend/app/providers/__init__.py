from backend.app.providers.base import MarketDataProvider
from backend.app.providers.static_provider import StaticDatabaseProvider
from backend.app.providers.live_mock import AuthorizedMCXLiveProvider
from backend.app.config import settings


def get_market_provider() -> MarketDataProvider:
    """
    Factory function returning the configured MarketDataProvider.
    Defaults to StaticDatabaseProvider for reliable, zero-config local operation.
    """
    if settings.data_mode == "live_feed_authorized" and settings.mcx_feed_api_key:
        return AuthorizedMCXLiveProvider()
    return StaticDatabaseProvider()


__all__ = ["MarketDataProvider", "StaticDatabaseProvider", "AuthorizedMCXLiveProvider", "get_market_provider"]
