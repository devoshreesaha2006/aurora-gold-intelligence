import os
import io
from datetime import date
from fastapi.testclient import TestClient
from backend.app.models.market_observation import MarketObservation
from backend.app.models.data_import import ImportBatch

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data")


def test_market_prices_excludes_synthetic_sample_data(client):
    # Keep the sample fixture explicitly synthetic; it must not be surfaced as
    # eligible market prices.
    csv_path = os.path.join(SAMPLE_DIR, "sample_mcx_gold_bhavcopy_valid.csv")
    with open(csv_path, "rb") as f:
        file_bytes = f.read()

    client.post(
        "/api/data/upload",
        files={"file": ("sample_mcx_gold_bhavcopy_valid.csv", io.BytesIO(file_bytes), "text/csv")},
        data={"data_source": "synthetic_seed", "is_synthetic": "true"}
    )

    res = client.get("/api/market/prices?limit=10&offset=0")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["items"] == []
    assert data["pagination"]["total"] == 0

    res_goldm = client.get("/api/market/prices?symbol=GOLDM")
    assert res_goldm.status_code == 200
    assert res_goldm.json()["data"]["items"] == []

    res_date = client.get("/api/market/prices?start_date=2026-10-14&end_date=2026-10-15")
    assert res_date.status_code == 200
    assert res_date.json()["data"]["items"] == []


def test_market_prices_excludes_test_and_synthetic_rows_but_keeps_eligible_csv(db_session):
    # Call the FastAPI route function directly here: the filtering behavior is
    # independent of Windows loopback/TestClient startup and remains testable.
    from backend.app.api.market import get_market_prices

    batch = ImportBatch(
        filename="test-only.csv", file_hash="a" * 64, total_rows=1,
        accepted_rows=1, data_source="test_invalid", is_synthetic=False,
    )
    db_session.add(batch)
    db_session.flush()
    db_session.add_all([
        MarketObservation(
            symbol="GOLDM", trade_date=date(2026, 10, 20), expiry_date=date(2026, 10, 30),
            close_price=62000, normalized_price_per_gram=6200,
            normalized_price_10g_basis=62000, data_source="test_run",
        ),
        MarketObservation(
            symbol="GOLDTEN", trade_date=date(2026, 10, 20), expiry_date=date(2026, 10, 30),
            close_price=62000, normalized_price_per_gram=6200,
            normalized_price_10g_basis=62000, data_source="csv_upload",
            import_batch_id=batch.id,
        ),
        MarketObservation(
            symbol="GOLDGUINEA", trade_date=date(2026, 10, 20), expiry_date=date(2026, 10, 30),
            close_price=62000, normalized_price_per_gram=6200,
            normalized_price_10g_basis=62000, data_source="synthetic_seed", is_synthetic=True,
        ),
        MarketObservation(
            symbol="GOLDPETAL", trade_date=date(2026, 10, 20), expiry_date=date(2026, 10, 30),
            close_price=62000, normalized_price_per_gram=6200,
            normalized_price_10g_basis=62000, data_source="csv_upload", is_synthetic=False,
        ),
    ])
    db_session.commit()

    response = get_market_prices(
        symbol=None, start_date=None, end_date=None, limit=50, offset=0, db=db_session,
    )
    assert response.success is True
    assert [item.symbol for item in response.data.items] == ["GOLDPETAL"]
    assert response.data.pagination.total == 1
    assert db_session.query(MarketObservation).count() == 4  # all remain stored for audit


def test_market_status_provider_error_is_a_non_success_response(client, monkeypatch):
    from backend.app.main import app

    def unavailable_provider():
        raise RuntimeError("provider adapter unavailable")

    monkeypatch.setattr("backend.app.api.market.get_market_provider", unavailable_provider)
    with TestClient(app, raise_server_exceptions=False) as isolated_client:
        response = isolated_client.get("/api/market/status")
    assert response.status_code == 500
