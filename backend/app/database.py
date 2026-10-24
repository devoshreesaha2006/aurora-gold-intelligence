from typing import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.schema import CreateColumn
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from backend.app.config import settings

# Configure database engine
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def upgrade_provider_timestamp_column() -> None:
    """Add provider and liquidity-field provenance columns without changing observations."""
    table_name = "market_observations"
    if table_name not in inspect(engine).get_table_names():
        return
    from backend.app.models.market_observation import MarketObservation
    existing_columns = {column["name"] for column in inspect(engine).get_columns(table_name)}
    missing = [name for name in (
        "provider_timestamp", "is_provider_verified", "volume_observed", "open_interest_observed"
    ) if name not in existing_columns]
    if missing:
        with engine.begin() as connection:
            for name in missing:
                column = MarketObservation.__table__.c[name]
                column_ddl = str(CreateColumn(column).compile(dialect=engine.dialect))
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_ddl}"))
                # Existing non-zero values are evidence that the field was
                # supplied. Legacy zeros are ambiguous, so treat them as
                # unavailable rather than asserting a zero-liquidity market.
                if name == "volume_observed":
                    connection.execute(text(
                        "UPDATE market_observations SET volume_observed = "
                        "CASE WHEN volume <> 0 THEN TRUE ELSE FALSE END"
                    ))
                elif name == "open_interest_observed":
                    connection.execute(text(
                        "UPDATE market_observations SET open_interest_observed = "
                        "CASE WHEN open_interest <> 0 THEN TRUE ELSE FALSE END"
                    ))
    # create_all cannot add indexes to a pre-existing table.
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_market_observations_provider_timestamp "
            "ON market_observations (provider_timestamp)"
        ))


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session per request.
    Automatically closes the session when the request is complete.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
