import os
import io
import pytest
from datetime import date
from sqlalchemy.orm import Session

from backend.app.services.analytics_service import (
    parse_pair, calculate_cost_hurdle, RelativeValueAnalyticsService,
    VALID_PAIRS
)
from backend.app.models.market_observation import MarketObservation
from backend.app.models.contract import Contract

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data")


def ingest_sample_bhavcopy(client):
    csv_path = os.path.join(SAMPLE_DIR, "sample_mcx_gold_bhavcopy_valid.csv")
    with open(csv_path, "rb") as f:
        file_bytes = f.read()

    client.post(
        "/api/data/upload",
        files={"file": ("sample_mcx_gold_bhavcopy_valid.csv", io.BytesIO(file_bytes), "text/csv")},
        data={"data_source": "synthetic_seed", "is_synthetic": "true"}
    )


# -----------------------------------------------------------------------------
# 1. Quantitative Logic & Unit Tests
# -----------------------------------------------------------------------------

def test_parse_pair():
    # Canonical
    a, b, inv = parse_pair("GOLDM-GOLDPETAL")
    assert a == "GOLDM" and b == "GOLDPETAL" and inv is False

    # Reversed
    a, b, inv = parse_pair("GOLDPETAL-GOLDM")
    assert a == "GOLDM" and b == "GOLDPETAL" and inv is True

    # Variations with slash / underscore
    a, b, inv = parse_pair("GOLDTEN/GOLDGUINEA")
    assert a == "GOLDTEN" and b == "GOLDGUINEA" and inv is False

    # Invalid
    with pytest.raises(ValueError):
        parse_pair("INVALID-GOLDM")
    with pytest.raises(ValueError):
        parse_pair("JUSTONE")


def test_cost_hurdle_calculation():
    hurdle = calculate_cost_hurdle(
        ref_price=62500.0,
        stt_rate_pct=0.01,
        exchange_fee_pct=0.0025,
        brokerage_per_10g=2.50,
        slippage_buffer_per_10g=15.00
    )
    # STT: 62500 * 0.0001 = 6.25
    # Exchange: 62500 * 0.000025 = 1.5625
    # Total = 6.25 + 1.5625 + 2.50 + 15.00 = 25.3125 -> 25.31
    assert abs(hurdle.total_roundtrip_cost_per_10g - 25.31) < 0.02


def test_classification_logic_all_states(db_session: Session):
    service = RelativeValueAnalyticsService(db_session)

    # 1. Expiry-Risk state (DTE <= 5 days)
    res_exp = service.classify_relative_value_state(
        spread=120.0, rolling_mean=14.0, z_score=2.4, percentile=98.0,
        dte_min=3, min_volume=5000, min_open_interest=10000, cost_hurdle=25.0
    )
    assert res_exp[0] == "Expiry-Risk"
    assert res_exp[3] is True # is_expiry_risk

    # 2. Cost-Blocked state (Gross edge <= cost hurdle)
    res_cost = service.classify_relative_value_state(
        spread=25.0, rolling_mean=15.0, z_score=1.8, percentile=90.0, # Gross edge = 10 <= 25
        dte_min=20, min_volume=5000, min_open_interest=10000, cost_hurdle=25.0
    )
    assert res_cost[0] == "Cost-Blocked"
    assert res_cost[4] is True # is_cost_blocked

    # 3. Watch state due to illiquidity (Z >= 1.5 but volume low)
    res_watch_liq = service.classify_relative_value_state(
        spread=100.0, rolling_mean=20.0, z_score=2.2, percentile=96.0,
        dte_min=20, min_volume=20, min_open_interest=50, cost_hurdle=25.0
    )
    assert res_watch_liq[0] == "Watch"
    assert res_watch_liq[5] is True # is_liquidity_trap

    # 4. Investigate state (Z >= 1.5, healthy liquidity, net edge > 0, DTE > 5)
    res_inv = service.classify_relative_value_state(
        spread=125.0, rolling_mean=15.0, z_score=2.5, percentile=97.5,
        dte_min=18, min_volume=2000, min_open_interest=5000, cost_hurdle=25.0
    )
    assert res_inv[0] == "Investigate"
    assert res_inv[1] > 60.0 # High opportunity score
    assert res_inv[7] == 85.0 # Net edge = (125-15) - 25 = 85.0

    # 5. No Signal state (Spread near mean, |Z| < 1.0)
    res_none = service.classify_relative_value_state(
        spread=16.0, rolling_mean=15.0, z_score=0.15, percentile=52.0,
        dte_min=20, min_volume=5000, min_open_interest=10000, cost_hurdle=25.0
    )
    assert res_none[0] == "No Signal"


def test_edge_cases_zero_variance_and_insufficient_history(db_session: Session):
    service = RelativeValueAnalyticsService(db_session)

    # Empty db test
    series = service.calculate_pairwise_spread_series("GOLDM", "GOLDPETAL")
    assert series.total_points == 0
    assert series.data_points == []

    # Distribution with empty data
    dist = service.get_spread_distribution("GOLDM-GOLDPETAL")
    assert dist.status == "insufficient_history"
    assert dist.sample_size == 0


# -----------------------------------------------------------------------------
# 2. REST API Integration Tests
# -----------------------------------------------------------------------------

def test_api_spreads_endpoint(client):
    ingest_sample_bhavcopy(client)

    # Fetch canonical pair GOLDM-GOLDPETAL
    res = client.get("/api/analytics/spreads?pair=GOLDM-GOLDPETAL&window=14")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert data["pair"] == "GOLDM-GOLDPETAL"
    assert data["total_points"] == 4 # 4 trading dates in sample data

    pts = data["data_points"]
    # Point 0 should be insufficient_history because N=1
    assert pts[0]["status"] == "insufficient_history"
    assert pts[0]["rolling_std"] is None
    assert pts[0]["z_score"] is None

    # Point 1 onwards has N >= 2, sample std dev and Z-score should exist
    assert pts[1]["status"] == "valid"
    assert pts[1]["rolling_std"] is not None
    assert pts[1]["z_score"] is not None
    assert pts[1]["percentile_rank"] is not None

    # Test inverted pair
    res_inv = client.get("/api/analytics/spreads?pair=GOLDPETAL-GOLDM")
    assert res_inv.status_code == 200
    data_inv = res_inv.json()["data"]
    assert data_inv["pair"] == "GOLDPETAL-GOLDM"
    # Spread should be exact negative
    assert abs(data_inv["data_points"][-1]["spread"] + pts[-1]["spread"]) < 0.01

    # Invalid pair returns 400
    res_bad = client.get("/api/analytics/spreads?pair=UNKNOWN-PAIR")
    assert res_bad.status_code == 400


def test_api_radar_endpoint(client):
    ingest_sample_bhavcopy(client)

    res = client.get("/api/analytics/radar?window=30")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]

    # Exactly 6 canonical pairs must be reported
    assert len(data["pairs"]) == 6
    pair_names = [p["pair"] for p in data["pairs"]]
    assert "GOLDM-GOLDTEN" in pair_names
    assert "GOLDM-GOLDGUINEA" in pair_names
    assert "GOLDM-GOLDPETAL" in pair_names
    assert "GOLDTEN-GOLDGUINEA" in pair_names
    assert "GOLDTEN-GOLDPETAL" in pair_names
    assert "GOLDGUINEA-GOLDPETAL" in pair_names

    for p in data["pairs"]:
        assert 0.0 <= p["deviation_intensity"] <= 100.0
        assert 0.0 <= p["opportunity_score"] <= 100.0
        assert 0.0 <= p["trap_risk_score"] <= 100.0
        assert p["classification"] in ("Investigate", "Watch", "Cost-Blocked", "Expiry-Risk", "No Signal")


def test_api_events_endpoint(client):
    ingest_sample_bhavcopy(client)

    res = client.get("/api/analytics/events?limit=20")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert "total_events" in data
    assert isinstance(data["items"], list)

    if data["items"]:
        evt = data["items"][0]
        assert evt["event_id"].startswith("EVT-")
        assert evt["severity"] in ("critical", "high", "medium", "low")
        assert evt["evidence"]["benchmark_basis"] == "₹ per 10g (995 fine gold equivalent)"
        assert evt["evidence"]["cost_hurdle"] > 0


def test_api_distribution_endpoint(client):
    ingest_sample_bhavcopy(client)

    res = client.get("/api/analytics/distribution?pair=GOLDM-GOLDPETAL&bins=10")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert data["status"] == "valid"
    assert data["sample_size"] == 4
    assert len(data["bins"]) == 10
    assert len(data["frequencies"]) == 10
    assert len(data["gaussian_pdf"]) == 10
    assert data["mean"] is not None
    assert data["sigma"] is not None


def test_asymmetric_dates_and_zero_future_leakage(db_session: Session):
    service = RelativeValueAnalyticsService(db_session)
    # Insert contract A with dates day 1, day 2, day 3
    # Insert contract B with dates day 2, day 3, day 4
    # The synchronized series must contain ONLY day 2 and day 3
    c_m = db_session.query(Contract).filter(Contract.symbol == "GOLDM").first()
    if not c_m:
        from backend.app.services.contract_service import seed_default_contracts
        seed_default_contracts(db_session)

    obs1 = MarketObservation(
        symbol="GOLDM", trade_date=date(2026, 11, 1), expiry_date=date(2026, 11, 28),
        close_price=62000.0, normalized_price_per_gram=6231.1558, normalized_price_10g_basis=62000.0
    )
    obs2 = MarketObservation(
        symbol="GOLDM", trade_date=date(2026, 11, 2), expiry_date=date(2026, 11, 28),
        close_price=62100.0, normalized_price_per_gram=6241.2060, normalized_price_10g_basis=62100.0
    )
    obs3 = MarketObservation(
        symbol="GOLDM", trade_date=date(2026, 11, 3), expiry_date=date(2026, 11, 28),
        close_price=62200.0, normalized_price_per_gram=6251.2563, normalized_price_10g_basis=62200.0
    )

    obs_b2 = MarketObservation(
        symbol="GOLDPETAL", trade_date=date(2026, 11, 2), expiry_date=date(2026, 11, 28),
        close_price=6270.0, normalized_price_per_gram=6276.2763, normalized_price_10g_basis=62448.95
    )
    obs_b3 = MarketObservation(
        symbol="GOLDPETAL", trade_date=date(2026, 11, 3), expiry_date=date(2026, 11, 28),
        close_price=6280.0, normalized_price_per_gram=6286.2863, normalized_price_10g_basis=62548.55
    )
    obs_b4 = MarketObservation(
        symbol="GOLDPETAL", trade_date=date(2026, 11, 4), expiry_date=date(2026, 11, 28),
        close_price=6290.0, normalized_price_per_gram=6296.2963, normalized_price_10g_basis=62648.15
    )

    db_session.add_all([obs1, obs2, obs3, obs_b2, obs_b3, obs_b4])
    db_session.commit()

    sync_pairs = service.get_synchronized_observations("GOLDM", "GOLDPETAL", start_date=date(2026, 11, 1), end_date=date(2026, 11, 4))
    dates = [a.trade_date for a, b in sync_pairs]
    assert dates == [date(2026, 11, 2), date(2026, 11, 3)]


def test_api_events_filtering_by_status_and_pair(client):
    ingest_sample_bhavcopy(client)

    # Filter by pair
    res_pair = client.get("/api/analytics/events?pair=GOLDM-GOLDPETAL")
    assert res_pair.status_code == 200
    for it in res_pair.json()["data"]["items"]:
        assert it["pair"] == "GOLDM-GOLDPETAL"

    # Filter with min_z
    res_z = client.get("/api/analytics/events?min_z=1.0")
    assert res_z.status_code == 200
    for it in res_z.json()["data"]["items"]:
        assert abs(it["evidence"]["z_score"]) >= 1.0
