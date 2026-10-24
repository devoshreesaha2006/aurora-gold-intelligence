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

def test_zero_open_price_is_treated_as_missing(client):
    csv_content = (
        b"symbol,trade_date,expiry_date,open,high,low,close,volume,open_interest\\n"
        b"GOLDM,2026-10-15,2026-10-30,0,63100,62710,62980,15400,37800\\n"
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

