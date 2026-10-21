from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from backend.app.schemas.market import MarketStatusRead
from backend.app.models.market_observation import MarketObservation


class MarketDataProvider(ABC):
    """
    Abstract interface for commodity market data feeds.
    Enables pluggable data sources: static database, CSV staging, or authorized live exchange feeds.
    """

    @abstractmethod
    def get_provider_name(self) -> str:
        """Returns the identifier name of this provider."""
        pass

    @abstractmethod
    def is_live_connected(self) -> bool:
        """Returns True ONLY if an authenticated live exchange socket/API is actively receiving packets."""
        pass

    @abstractmethod
    def get_market_status(self, db: Session) -> MarketStatusRead:
        """Computes current data status, observations count, and data freshness."""
        pass

    @abstractmethod
    def fetch_latest_observations(self, db: Session, limit: int = 100) -> List[MarketObservation]:
        """Fetches recent observations for dashboard visualization."""
        pass
