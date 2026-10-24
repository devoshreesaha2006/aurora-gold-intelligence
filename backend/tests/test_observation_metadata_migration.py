from sqlalchemy import create_engine, text

import backend.app.database as database_module


def test_additive_observation_metadata_migration_preserves_rows(monkeypatch):
    legacy_engine = create_engine("sqlite:///:memory:")
    with legacy_engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE market_observations ("
            "id INTEGER PRIMARY KEY, volume INTEGER NOT NULL, open_interest INTEGER NOT NULL)"
        ))
        connection.execute(text(
            "INSERT INTO market_observations (id, volume, open_interest) VALUES "
            "(1, 0, 0), (2, 120, 800)"
        ))
    monkeypatch.setattr(database_module, "engine", legacy_engine)

    database_module.upgrade_provider_timestamp_column()

    with legacy_engine.connect() as connection:
        rows = connection.execute(text(
            "SELECT id, volume, open_interest, volume_observed, open_interest_observed "
            "FROM market_observations ORDER BY id"
        )).mappings().all()
    assert [dict(row) for row in rows] == [
        {"id": 1, "volume": 0, "open_interest": 0, "volume_observed": 0, "open_interest_observed": 0},
        {"id": 2, "volume": 120, "open_interest": 800, "volume_observed": 1, "open_interest_observed": 1},
    ]
    legacy_engine.dispose()
