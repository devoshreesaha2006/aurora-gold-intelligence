from datetime import date

from backend.app.models.market_observation import MarketObservation


def test_research_forecast_does_not_fabricate_missing_history(client):
    response = client.get("/api/research/forecast?symbol=GOLDM")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "insufficient_history"
    assert payload["forecast"] == []


def test_risk_sizing_uses_explicit_inputs(client):
    response = client.post("/api/research/risk-sizing", json={
        "capital": 100000, "risk_pct": 1, "entry_price": 100,
        "stop_price": 90, "unit_size": 1, "estimated_cost_per_unit": 5,
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_budget"] == 1000
    assert payload["estimated_risk_per_unit"] == 15
    assert payload["max_units_by_input_assumptions"] == 66


def test_risk_sizing_rejects_identical_entry_and_stop(client):
    response = client.post("/api/research/risk-sizing", json={
        "capital": 100000, "risk_pct": 1, "entry_price": 100,
        "stop_price": 100, "unit_size": 1, "estimated_cost_per_unit": 0,
    })
    assert response.status_code == 422


def test_macro_and_calendar_explicitly_report_unconfigured(client):
    macro = client.get("/api/research/macro-context")
    calendar = client.get("/api/research/event-calendar")
    assert macro.status_code == 200
    assert macro.json()["status"] == "not_configured"
    assert all(item["value"] is None for item in macro.json()["items"])
    assert calendar.status_code == 200
    assert calendar.json()["status"] == "not_configured"
    assert calendar.json()["events"] == []


def test_observation_export_is_csv_and_uses_actual_model_fields(client, db_session):
    db_session.add(MarketObservation(
        symbol="GOLDM", trade_date=date(2026, 10, 1), expiry_date=date(2026, 10, 30),
        close_price=145000, normalized_price_per_gram=14500,
        normalized_price_10g_basis=144275, volume=10, open_interest=20,
        data_source="csv_upload", is_synthetic=False, is_provider_verified=False,
    ))
    db_session.commit()
    response = client.get("/api/research/export-observations?symbol=GOLDM")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "145000" in response.text
    assert "provider_verified" in response.text
