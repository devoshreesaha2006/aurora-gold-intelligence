"""Shared source-label checks for excluding test and synthetic observations."""

from sqlalchemy import func, or_

TEST_SOURCES = {"test", "test_run", "test_invalid", "tests", "pytest", "fixture"}
SYNTHETIC_SOURCES = {"synthetic", "synthetic_seed", "demo_synthetic", "sample_data"}


def normalized_source(value):
    return (value or "").strip().lower()


def is_test_source(value):
    source = normalized_source(value)
    return source in TEST_SOURCES or source.startswith(("test_", "tests_", "invalid_", "fixture_", "pytest_"))


def is_synthetic_source(value):
    source = normalized_source(value)
    return source in SYNTHETIC_SOURCES or source.startswith(("synthetic_", "demo_", "sample_"))


def test_source_condition(column):
    """SQL equivalent of is_test_source for row and import-batch filters."""
    source = func.lower(func.coalesce(column, ""))
    return or_(
        source.in_(TEST_SOURCES),
        source.startswith("test_", autoescape=True),
        source.startswith("tests_", autoescape=True),
        source.startswith("invalid_", autoescape=True),
        source.startswith("fixture_", autoescape=True),
        source.startswith("pytest_", autoescape=True),
    )


def synthetic_source_condition(column):
    """SQL equivalent of is_synthetic_source for observation/import sources."""
    source = func.lower(func.coalesce(column, ""))
    return or_(
        source.in_(SYNTHETIC_SOURCES),
        source.startswith("synthetic_", autoescape=True),
        source.startswith("demo_", autoescape=True),
        source.startswith("sample_", autoescape=True),
    )


def non_test_observations_query(db):
    """Return observations excluding rows or batches explicitly marked as test data."""
    from sqlalchemy import not_, or_
    from backend.app.models.data_import import ImportBatch
    from backend.app.models.market_observation import MarketObservation

    test_rows = or_(
        test_source_condition(MarketObservation.data_source),
        test_source_condition(ImportBatch.data_source),
    )
    return (
        db.query(MarketObservation)
        .outerjoin(ImportBatch, MarketObservation.import_batch_id == ImportBatch.id)
        .filter(not_(test_rows))
    )


def eligible_analytics_observations_query(db):
    """Return imported/provider observations, excluding test and synthetic sources."""
    from sqlalchemy import not_, or_
    from backend.app.models.data_import import ImportBatch
    from backend.app.models.market_observation import MarketObservation

    ineligible = or_(
        test_source_condition(MarketObservation.data_source),
        test_source_condition(ImportBatch.data_source),
        MarketObservation.is_synthetic.is_(True),
        ImportBatch.is_synthetic.is_(True),
        synthetic_source_condition(MarketObservation.data_source),
        synthetic_source_condition(ImportBatch.data_source),
    )
    return (
        db.query(MarketObservation)
        .outerjoin(ImportBatch, MarketObservation.import_batch_id == ImportBatch.id)
        .filter(not_(ineligible))
    )
