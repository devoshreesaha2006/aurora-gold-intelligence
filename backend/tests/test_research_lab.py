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


def test_forecast_validation_reports_insufficient_history_without_fabrication(client):
    response = client.get("/api/research/forecast-validation?symbol=GOLDM")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "insufficient_history"
    assert payload["folds"] == []
    assert payload["metrics"] is None


def test_forecast_validation_is_chronological_and_compares_baselines(client, db_session):
    # 45 distinct dates with a deterministic upward series.
    from datetime import timedelta

    start = date(2026, 1, 1)
    for index in range(45):
        price = 100000 + index * 100 + (index % 4) * 12
        db_session.add(MarketObservation(
            symbol="GOLDM",
            trade_date=start + timedelta(days=index),
            expiry_date=date(2026, 12, 31),
            close_price=price,
            normalized_price_per_gram=price / 10,
            normalized_price_10g_basis=price,
            volume=100 + index,
            open_interest=200 + index,
            data_source="csv_upload",
            is_synthetic=False,
            is_provider_verified=False,
        ))
    db_session.commit()

    response = client.get(
        "/api/research/forecast-validation?symbol=GOLDM&lookback=30&min_train=20&max_folds=10"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "evaluated"
    assert payload["test_folds"] == 10
    assert payload["first_test_date"] < payload["last_test_date"]
    assert payload["models"]["naive_last_value"]["mae"] >= 0
    assert payload["models"]["linear_trend"]["rmse"] >= 0
    assert payload["models"]["rolling_mean_5"]["mae"] >= 0
    assert payload["selection"]["lowest_mae_model"] in {"naive_last_value", "rolling_mean_5", "linear_trend"}
    assert "directional_accuracy_pct" in payload["models"]["naive_last_value"]
    assert "rolling_mean_prediction_10g" in payload["folds"][0]
    assert len(payload["folds"]) == 10
    assert all(fold["training_observations"] <= 30 for fold in payload["folds"])
    assert "only earlier" in payload["method"]


def test_forecast_horizon_validation_reports_insufficient_history(client):
    response = client.get("/api/research/forecast-horizon-validation?symbol=GOLDM&horizon=5")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "insufficient_history"
    assert payload["folds"] == []
    assert payload["metrics"] is None


def test_forecast_horizon_validation_uses_future_target_without_leakage(client, db_session):
    from datetime import timedelta

    start = date(2026, 1, 1)
    for index in range(55):
        price = 100000 + index * 120 + (index % 5) * 18
        db_session.add(MarketObservation(
            symbol="GOLDM", trade_date=start + timedelta(days=index),
            expiry_date=date(2026, 12, 31), close_price=price,
            normalized_price_per_gram=price / 10,
            normalized_price_10g_basis=price, volume=100 + index,
            open_interest=200 + index, data_source="csv_upload",
            is_synthetic=False, is_provider_verified=False,
        ))
    db_session.commit()

    response = client.get(
        "/api/research/forecast-horizon-validation?symbol=GOLDM&horizon=5&lookback=30&min_train=20&max_folds=10"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "evaluated"
    assert payload["horizon_observations"] == 5
    assert payload["test_folds"] == 10
    assert payload["first_target_date"] < payload["last_target_date"]
    assert payload["models"]["naive_last_value"]["mae"] >= 0
    assert payload["models"]["rolling_mean_5"]["rmse"] >= 0
    assert payload["models"]["linear_trend"]["mape_pct"] >= 0
    assert all(fold["horizon_observations"] == 5 for fold in payload["folds"])
    assert all(fold["target_date"] > fold["origin_date"] for fold in payload["folds"])
    assert all(fold["training_observations"] <= 30 for fold in payload["folds"])
    assert "only observations available at its origin" in payload["method"]



def test_forecast_exposes_all_baselines_without_removing_trend_compatibility(client, db_session):
    from datetime import timedelta

    start = date(2026, 1, 1)
    for index in range(45):
        price = 100000 + index * 100 + (index % 4) * 12
        db_session.add(MarketObservation(
            symbol="GOLDM", trade_date=start + timedelta(days=index),
            expiry_date=date(2026, 12, 31), close_price=price,
            normalized_price_per_gram=price / 10,
            normalized_price_10g_basis=price, volume=100 + index,
            open_interest=200 + index, data_source="csv_upload",
            is_synthetic=False, is_provider_verified=False,
        ))
    db_session.commit()

    response = client.get("/api/research/forecast?symbol=GOLDM&lookback=30&horizon=3")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "baseline_only"
    assert len(payload["forecast"]) == 3
    for step in payload["forecast"]:
        assert step["baseline_price_10g"] == step["model_forecasts"]["linear_trend"]
        assert set(step["model_forecasts"]) == {"naive_last_value", "rolling_mean_5", "linear_trend"}
        assert all(value > 0 for value in step["model_forecasts"].values())



def test_forecast_stability_compares_separate_chronological_windows(client, db_session):
    from datetime import timedelta

    start = date(2026, 1, 1)
    for index in range(100):
        # Deterministic, non-flat history for chronological diagnostics only.
        price = 100000 + index * 75 + (index % 7) * 90
        db_session.add(MarketObservation(
            symbol="GOLDM", trade_date=start + timedelta(days=index),
            expiry_date=date(2026, 12, 31), close_price=price,
            normalized_price_per_gram=price / 10,
            normalized_price_10g_basis=price, volume=100 + index,
            open_interest=200 + index, data_source="csv_upload",
            is_synthetic=False, is_provider_verified=False,
        ))
    db_session.commit()

    response = client.get(
        "/api/research/forecast-stability?symbol=GOLDM&horizon=5&lookback=30&min_train=20&windows=3&folds_per_window=10"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "evaluated"
    assert len(payload["windows"]) == 3
    assert payload["test_folds"] == 30
    assert payload["first_target_date"] < payload["last_target_date"]
    assert payload["overall_lowest_mae_model"] in {"naive_last_value", "rolling_mean_5", "linear_trend"}
    assert payload["stability_verdict"] in {"consistent", "window_dependent"}
    assert sum(payload["window_wins"].values()) == 3
    assert all(window["first_target_date"] <= window["last_target_date"] for window in payload["windows"])
    assert all(window["winner"] in {"naive_last_value", "rolling_mean_5", "linear_trend"} for window in payload["windows"])


def test_forecast_stability_reports_insufficient_history(client):
    response = client.get(
        "/api/research/forecast-stability?symbol=GOLDM&horizon=5&windows=3&folds_per_window=10"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "insufficient_history"
    assert payload["windows"] == []
    assert payload["minimum_required"] > payload["observations"]
