"""Ensure SQL provenance filters match their Python source-label rules."""

import pytest
from sqlalchemy import create_engine, literal, select

from backend.app.services.data_provenance import (
    is_synthetic_source,
    is_test_source,
    synthetic_source_condition,
    sql_test_source_condition,
)


@pytest.fixture
def sqlite_connection():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        yield connection
    engine.dispose()


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("test", True),
        ("TEST_RUN", True),
        (" test_custom ", True),
        ("tests_fixture", True),
        ("invalid_import", True),
        ("fixture_data", True),
        ("pytest_case", True),
        ("test-run", False),
        ("testXrun", False),
        ("contest_data", False),
        ("csv_upload", False),
        ("", False),
        (None, False),
    ],
)
def test_sql_test_source_condition_matches_python(sqlite_connection, source, expected):
    sql_result = sqlite_connection.execute(
        select(sql_test_source_condition(literal(source)))
    ).scalar_one()

    assert is_test_source(source) is expected
    assert bool(sql_result) is expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("synthetic", True),
        ("SYNTHETIC_SEED", True),
        ("synthetic_history", True),
        ("demo_generated", True),
        ("sample_fixture", True),
        ("synthetic-data", False),
        ("syntheticXseed", False),
        ("real_csv_upload", False),
        ("", False),
        (None, False),
    ],
)
def test_sql_synthetic_source_condition_matches_python(sqlite_connection, source, expected):
    sql_result = sqlite_connection.execute(
        select(synthetic_source_condition(literal(source)))
    ).scalar_one()

    assert is_synthetic_source(source) is expected
    assert bool(sql_result) is expected
