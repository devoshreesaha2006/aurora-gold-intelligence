def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["database"] == "connected"
    assert "version" in data["data"]
    assert "server_time" in data["data"]


def test_market_status(client):
    response = client.get("/api/market/status")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    payload = data["data"]
    assert "market_open" in payload
    assert payload["total_contracts_tracked"] >= 4
    assert payload["is_live_connected"] is False  # In demo/staged mode
    assert "data_freshness_label" in payload
