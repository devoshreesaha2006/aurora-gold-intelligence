import os
import io

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data")


def test_valid_csv_upload(client):
    csv_path = os.path.join(SAMPLE_DIR, "sample_mcx_gold_bhavcopy_valid.csv")
    with open(csv_path, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/data/upload",
        files={"file": ("sample_mcx_gold_bhavcopy_valid.csv", io.BytesIO(file_bytes), "text/csv")},
        data={"data_source": "test_synthetic", "is_synthetic": "true"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    upload_result = data["data"]
    assert upload_result["accepted_rows"] == 16
    assert upload_result["rejected_rows"] == 0
    assert upload_result["status"] == "completed"
    assert upload_result["batch_id"] > 0


def test_duplicate_csv_prevention(client):
    csv_content = b"symbol,trade_date,expiry_date,open,high,low,close,volume,open_interest\nGOLDM,2026-10-15,2026-10-30,62790,63100,62710,62980,15400,37800\n"

    # First upload
    res1 = client.post(
        "/api/data/upload",
        files={"file": ("dedup_test.csv", io.BytesIO(csv_content), "text/csv")},
        data={"data_source": "test_dedup"}
    )
    assert res1.status_code == 200
    assert res1.json()["data"]["accepted_rows"] == 1

    # Second upload with identical file content
    res2 = client.post(
        "/api/data/upload",
        files={"file": ("dedup_test.csv", io.BytesIO(csv_content), "text/csv")},
        data={"data_source": "test_dedup", "allow_duplicates": "false"}
    )
    assert res2.status_code == 200
    data2 = res2.json()["data"]
    assert "Duplicate file ignored" in data2["message"]
    assert data2["accepted_rows"] == 0
    assert data2["duplicate_rows"] == 1
    assert data2["status"] == "completed"


def test_invalid_csv_validation_report(client):
    csv_path = os.path.join(SAMPLE_DIR, "sample_mcx_gold_bhavcopy_invalid.csv")
    with open(csv_path, "rb") as f:
        file_bytes = f.read()

    response = client.post(
        "/api/data/upload",
        files={"file": ("sample_mcx_gold_bhavcopy_invalid.csv", io.BytesIO(file_bytes), "text/csv")},
        data={"data_source": "test_invalid"}
    )
    assert response.status_code == 200
    data = response.json()
    upload_result = data["data"]
    # 1 valid row (GOLDM), 7 rejected rows
    assert upload_result["accepted_rows"] == 1
    assert upload_result["rejected_rows"] == 7
    assert len(upload_result["errors"]) == 7

    reasons = [e["reason"] for e in upload_result["errors"]]
    assert any("SILVERM" in r for r in reasons)
    assert any("Close price must be positive" in r for r in reasons)
    assert any("High price" in r and "cannot be lower than Low" in r for r in reasons)
    assert any("close" in e["field"] for e in upload_result["errors"])
    assert any("date format" in r for r in reasons)
    assert any("cannot be earlier than trade date" in r for r in reasons)
    assert any("Volume cannot be negative" in r for r in reasons)


def test_list_data_imports(client):
    # Upload one batch
    csv_content = b"symbol,trade_date,expiry_date,close\nGOLDM,2026-10-15,2026-10-30,62980\n"
    client.post(
        "/api/data/upload",
        files={"file": ("batch_test.csv", io.BytesIO(csv_content), "text/csv")}
    )

    response = client.get("/api/data/imports")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert len(data["data"]) >= 1
    assert data["data"][0]["filename"] == "batch_test.csv"


def test_database_persistence_and_relationships(client, db_session):
    from backend.app.models.market_observation import MarketObservation
    from backend.app.models.data_import import ImportBatch

    csv_content = b"symbol,trade_date,expiry_date,open,high,low,close,volume,open_interest\nGOLDTEN,2026-10-15,2026-11-27,62700,62990,62630,62890,3850,9720\n"
    res = client.post(
        "/api/data/upload",
        files={"file": ("persistence_test.csv", io.BytesIO(csv_content), "text/csv")},
        data={"data_source": "test_persistence"}
    )
    assert res.status_code == 200
    batch_id = res.json()["data"]["batch_id"]

    # Directly verify in DB session
    batch = db_session.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
    assert batch is not None
    assert batch.filename == "persistence_test.csv"
    assert batch.accepted_rows == 1

    obs = db_session.query(MarketObservation).filter(
        MarketObservation.symbol == "GOLDTEN",
        MarketObservation.import_batch_id == batch_id
    ).first()
    assert obs is not None
    assert obs.close_price == 62890.0
    assert obs.volume == 3850
    assert obs.open_interest == 9720
    assert obs.normalized_price_per_gram > 0
    assert obs.normalized_price_10g_basis > 0

def test_zero_open_price_is_treated_as_missing(client, db_session):
    from datetime import date
    from backend.app.models.market_observation import MarketObservation

    csv_content = (
        b"symbol,trade_date,expiry_date,open,high,low,close,volume,open_interest\n"
        b"GOLDM,2026-10-15,2026-10-30,0,63100,62710,62980,15400,37800\n"
    )
    response = client.post(
        "/api/data/upload",
        files={"file": ("zero_open_test.csv", io.BytesIO(csv_content), "text/csv")},
        data={"data_source": "test_zero_open"}
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["accepted_rows"] == 1
    assert result["rejected_rows"] == 0

    observation = db_session.query(MarketObservation).filter(
        MarketObservation.symbol == "GOLDM",
        MarketObservation.trade_date == date(2026, 10, 15),
        MarketObservation.expiry_date == date(2026, 10, 30),
    ).first()
    assert observation is not None
    assert observation.open_price is None
    assert observation.high_price == 63100.0
    assert observation.low_price == 62710.0


def test_zero_high_and_low_prices_are_treated_as_missing(client, db_session):
    from datetime import date
    from backend.app.models.market_observation import MarketObservation

    csv_content = (
        b"symbol,trade_date,expiry_date,open,high,low,close,volume,open_interest\n"
        b"GOLDTEN,2026-10-16,2026-11-27,0,0,0,62890,3850,9720\n"
    )
    response = client.post(
        "/api/data/upload",
        files={"file": ("zero_high_low_test.csv", io.BytesIO(csv_content), "text/csv")},
        data={"data_source": "test_zero_ohl"}
    )
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["accepted_rows"] == 1
    assert result["rejected_rows"] == 0

    observation = db_session.query(MarketObservation).filter(
        MarketObservation.symbol == "GOLDTEN",
        MarketObservation.trade_date == date(2026, 10, 16),
        MarketObservation.expiry_date == date(2026, 11, 27),
    ).first()
    assert observation is not None
    assert observation.open_price is None
    assert observation.high_price is None
    assert observation.low_price is None
    assert observation.close_price == 62890.0


def test_import_with_skipped_duplicates_and_rejected_rows_is_partial_success(db_session):
    from backend.app.models.data_import import ImportBatch
    from backend.app.schemas.ingestion import ImportBatchRead
    from backend.app.services.ingestion_service import CsvIngestionService

    valid = b"symbol,trade_date,expiry_date,close\nGOLDM,2026-10-15,2026-10-30,62980\n"
    service = CsvIngestionService(db_session)
    first = service.process_csv(valid, "initial.csv")
    assert first.accepted_rows == 1

    mixed = (
        b"symbol,trade_date,expiry_date,close\n"
        b"GOLDM,2026-10-15,2026-10-30,62980\n"
        b"GOLDTEN,2026-10-15,2026-11-27,-1\n"
    )
    result = service.process_csv(mixed, "mixed.csv")
    assert result.total_rows == 2
    assert result.accepted_rows == 0
    assert result.rejected_rows == 1
    assert result.duplicate_rows == 1
    assert result.status == "partial_success"

    batch = db_session.query(ImportBatch).filter(ImportBatch.filename == "mixed.csv").one()
    response_batch = ImportBatchRead.model_validate(batch)
    assert response_batch.duplicate_rows == 1
    assert response_batch.status == "partial_success"


def test_import_history_status_distinguishes_failure_from_skipped_duplicates():
    from datetime import datetime, timezone
    from backend.app.schemas.ingestion import ImportBatchRead

    def batch(total, accepted, rejected):
        return ImportBatchRead(
            id=1, filename="audit.csv", file_hash="a" * 64, total_rows=total,
            accepted_rows=accepted, rejected_rows=rejected, data_source="csv_upload",
            is_synthetic=False, created_at=datetime.now(timezone.utc),
        )

    assert batch(3, 2, 1).status == "partial_success"
    assert batch(2, 0, 1).status == "partial_success"  # one duplicate was skipped
    assert batch(1, 0, 1).status == "failed"
    assert batch(2, 0, 0).status == "completed"  # both rows were duplicates


def test_import_history_timestamp_is_explicit_utc_when_sqlite_returns_naive():
    from datetime import datetime, timezone
    from backend.app.schemas.ingestion import ImportBatchRead

    batch = ImportBatchRead(
        id=1, filename="audit.csv", file_hash="a" * 64, total_rows=1,
        accepted_rows=1, rejected_rows=0, data_source="csv_upload",
        is_synthetic=False, created_at=datetime(2026, 10, 25, 7, 19, 58),
    )

    assert batch.created_at.tzinfo is timezone.utc
    assert batch.created_at.isoformat() == "2026-10-25T07:19:58+00:00"
