def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["database"] == "connected"
    assert "version" in data["data"]
    assert "server_time" in data["data"]

    # Health and market status must describe the same effective data source.
    market_response = client.get("/api/market/status")
    assert market_response.status_code == 200
    assert data["data"]["data_mode"] == market_response.json()["data"]["data_mode"]


def test_market_status(client):
    response = client.get("/api/market/status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    payload = data["data"]
    assert "market_open" in payload
    assert payload["market_open"] is None
    assert payload["market_session_status"] == "unknown"
    assert payload["total_contracts_tracked"] >= 4
    assert payload["is_live_connected"] is False  # In demo/staged mode
    assert "data_freshness_label" in payload
    assert payload["feed_status"] == "UNAVAILABLE"
    assert payload["data_provenance"]
    assert payload["market_open"] is None
    assert payload["market_session_status"] == "unknown"
    assert "·" in payload["data_freshness_label"]
    assert "Â·" not in payload["data_freshness_label"]
