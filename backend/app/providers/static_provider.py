from datetime import datetime, timezone, time, date
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.providers.base import MarketDataProvider
from backend.app.schemas.market import MarketStatusRead
from backend.app.models.contract import Contract
from backend.app.models.market_observation import MarketObservation
from backend.app.models.data_import import ImportBatch
from backend.app.config import settings


class StaticDatabaseProvider(MarketDataProvider):
    """
    Local Database & CSV provider.
    Operates without external API credentials.
    Transparently labels data source mode as 'staged_csv' or 'demo_synthetic'.
    """

    def get_provider_name(self) -> str:
        return "AURORA Local Database & CSV Ingestion Engine"

    def is_live_connected(self) -> bool:
        return False

    def _is_market_session_open(self) -> bool:
        """
        Calculates whether the current IST time is within MCX bullion trading hours:
        Monday-Friday: 09:00 - 23:30 / 23:55 IST.
        """
        now = datetime.now()
        # Monday=0, Sunday=6
        if now.weekday() >= 5:
            return False
        current_time = now.time()
        market_start = time(9, 0)
        market_end = time(23, 30)
        return market_start <= current_time <= market_end

    def get_market_status(self, db: Session) -> MarketStatusRead:
        total_contracts = db.query(Contract).filter(Contract.is_active == True).count()
        total_obs = db.query(MarketObservation).count()

        latest_obs = db.query(MarketObservation).order_by(MarketObservation.trade_date.desc()).first()
        latest_date = latest_obs.trade_date if latest_obs else None

        last_batch = db.query(ImportBatch).order_by(ImportBatch.created_at.desc()).first()
        last_ingestion = last_batch.created_at if last_batch else None

        # Determine explicit data mode
        has_real_csv = db.query(MarketObservation).filter(MarketObservation.is_synthetic == False).first() is not None
        if has_real_csv:
            mode = "staged_csv"
            freshness = f"Historical Bhavcopy (Latest: {latest_date})" if latest_date else "Staged CSV (Empty)"
        else:
            mode = settings.data_mode
            freshness = "Synthetic Demo Dataset" if total_obs > 0 else "No Data Ingested (Awaiting CSV)"

        return MarketStatusRead(
            market_open=self._is_market_session_open(),
            data_mode=mode,
            provider_name=self.get_provider_name(),
            is_live_connected=False,
            total_contracts_tracked=total_contracts,
            total_observations=total_obs,
            last_ingestion_at=last_ingestion,
            latest_trade_date=latest_date,
            server_time=datetime.now(timezone.utc),
            data_freshness_label=freshness
        )

    def fetch_latest_observations(self, db: Session, limit: int = 100) -> List[MarketObservation]:
        return (
            db.query(MarketObservation)
            .order_by(MarketObservation.trade_date.desc(), MarketObservation.symbol.asc())
            .limit(limit)
            .all()
        )
