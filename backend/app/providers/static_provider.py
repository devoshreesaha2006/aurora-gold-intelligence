from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func, not_, or_

from backend.app.providers.base import MarketDataProvider
from backend.app.schemas.market import MarketStatusRead
from backend.app.models.contract import Contract
from backend.app.models.market_observation import MarketObservation
from backend.app.models.data_import import ImportBatch
from backend.app.config import settings
from backend.app.services.data_provenance import is_synthetic_source, is_test_source


def _source_condition(column, predicate):
    """Build a SQL condition equivalent to the shared provenance source checks."""
    source = func.lower(func.coalesce(column, ""))
    if predicate is is_test_source:
        exact = ("test", "test_run", "test_invalid", "tests", "pytest", "fixture")
        prefixes = ("test_%", "tests_%", "invalid_%", "fixture_%", "pytest_%")
    else:
        exact = ("synthetic", "synthetic_seed", "demo_synthetic", "sample_data")
        prefixes = ("synthetic_%", "demo_%", "sample_%")
    return or_(source.in_(exact), *(source.like(prefix) for prefix in prefixes))


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

    def get_market_status(self, db: Session) -> MarketStatusRead:
        total_contracts = db.query(Contract).filter(Contract.is_active == True).count()
        total_obs = db.query(MarketObservation).count()

        latest_obs = db.query(MarketObservation).order_by(MarketObservation.trade_date.desc()).first()
        latest_date = latest_obs.trade_date if latest_obs else None

        last_batch = db.query(ImportBatch).order_by(ImportBatch.created_at.desc()).first()
        last_ingestion = last_batch.created_at if last_batch else None

        # CSV uploads are user-provided and are not verified exchange/provider data.
        # Batch-level provenance takes precedence so test/synthetic batches cannot
        # become "historical Bhavcopy" merely because an individual row flag is false.
        joined = db.query(MarketObservation, ImportBatch).outerjoin(
            ImportBatch, MarketObservation.import_batch_id == ImportBatch.id
        )
        is_test = or_(
            _source_condition(MarketObservation.data_source, is_test_source),
            _source_condition(ImportBatch.data_source, is_test_source),
        )
        is_synthetic = or_(
            MarketObservation.is_synthetic.is_(True),
            ImportBatch.is_synthetic.is_(True),
            _source_condition(MarketObservation.data_source, is_synthetic_source),
            _source_condition(ImportBatch.data_source, is_synthetic_source),
        )
        test_count = joined.filter(is_test).count()
        synthetic_count = joined.filter(and_(not_(is_test), is_synthetic)).count()
        csv_count = joined.filter(and_(not_(is_test), not_(is_synthetic))).count()

        labels = []
        if csv_count:
            labels.append("User-imported historical CSV (not provider-verified)")
        if synthetic_count:
            labels.append("Synthetic data present")
        if test_count:
            labels.append("Test data present")
        if not labels:
            labels.append("No data ingested (awaiting CSV)")
        labels.append("No verified provider observations")

        if csv_count:
            mode = "staged_csv"  # Retained for existing clients; label explicitly states unverified provenance.
        elif test_count:
            mode = "test_data"
        elif synthetic_count:
            mode = "demo_synthetic"
        else:
            mode = "live_feed_disconnected" if settings.data_mode == "live_feed_authorized" else settings.data_mode
        freshness = " · ".join(labels)

        return MarketStatusRead(
            market_open=None,
            market_session_status="unknown",
            data_mode=mode,
            provider_name=self.get_provider_name(),
            is_live_connected=False,
            total_contracts_tracked=total_contracts,
            total_observations=total_obs,
            last_ingestion_at=last_ingestion,
            latest_trade_date=latest_date,
            server_time=datetime.now(timezone.utc),
            data_freshness_label=freshness,
            feed_status="UNAVAILABLE",
            connection_state="disconnected",
            authentication_state="not_applicable",
            data_provenance="; ".join(labels),
        )

    def fetch_latest_observations(self, db: Session, limit: int = 100) -> List[MarketObservation]:
        return (
            db.query(MarketObservation)
            .order_by(MarketObservation.trade_date.desc(), MarketObservation.symbol.asc())
            .limit(limit)
            .all()
        )
