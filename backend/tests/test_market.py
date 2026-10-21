import os
import io

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data")


def test_market_prices_query_and_pagination(client):
    # Ingest valid sample data first
    csv_path = os.path.join(SAMPLE_DIR, "sample_mcx_gold_bhavcopy_valid.csv")
    with open(csv_path, "rb") as f:
        file_bytes = f.read()

    client.post(
        "/api/data/upload",
        files={"file": ("sample_mcx_gold_bhavcopy_valid.csv", io.BytesIO(file_bytes), "text/csv")},
        data={"data_source": "synthetic_seed", "is_synthetic": "true"}
    )

    # 1. Fetch all prices (limit 10)
    res = client.get("/api/market/prices?limit=10&offset=0")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data["items"]) == 10
    assert data["pagination"]["total"] == 16
    assert data["pagination"]["has_more"] is True

    # Check normalized price presence
    first_item = data["items"][0]
    assert first_item["normalized_price_per_gram"] > 0
    assert first_item["normalized_price_10g_basis"] > 0
    assert first_item["close_price"] > 0

    # 2. Filter by Symbol = GOLDM
    res_goldm = client.get("/api/market/prices?symbol=GOLDM")
    assert res_goldm.status_code == 200
    items_goldm = res_goldm.json()["data"]["items"]
    assert len(items_goldm) == 4
    for it in items_goldm:
        assert it["symbol"] == "GOLDM"

    # 3. Filter by date bounds
    res_date = client.get("/api/market/prices?start_date=2026-10-14&end_date=2026-10-15")
    assert res_date.status_code == 200
    items_date = res_date.json()["data"]["items"]
    # 4 contracts * 2 days = 8 items
    assert len(items_date) == 8
