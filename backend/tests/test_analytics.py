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
from backend.app.schemas.analytics import EventEvidenceTrail
from backend.app.services.ingestion_service import CsvIngestionService

SAMPLE_DIR = os.path.join(os.path.dirname(__file__), "..", "sample_data")


def ingest_sample_bhavcopy(client):
    csv_path = os.path.join(SAMPLE_DIR, "sample_mcx_gold_bhavcopy_valid.csv")
    with open(csv_path, "rb") as f:
        file_bytes = f.read()

    # Keep this synthetic fixture synchronized by expiry so analytics tests exercise
    # valid same-expiry pairings under the production matching rule.
    file_bytes = file_bytes.replace(b"2026-11-27", b"2026-10-30").replace(b"2026-10-28", b"2026-10-30")

    client.post(
        "/api/data/upload",
        files={"file": ("sample_mcx_gold_bhavcopy_valid.csv", io.BytesIO(file_bytes), "text/csv")},
        # This fixture exercises the user-imported CSV analytics path in an
        # isolated test database; synthetic/demo provenance is excluded by API analytics.
        data={"data_source": "csv_upload", "is_synthetic": "false"}
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


def test_missing_statistical_baseline_or_liquidity_is_not_a_liquidity_trap(db_session: Session):
    service = RelativeValueAnalyticsService(db_session)
    insufficient = service.classify_relative_value_state(
        spread=10.0, rolling_mean=10.0, z_score=None, percentile=None,
        dte_min=None, min_volume=0, min_open_interest=0, cost_hurdle=25.0
    )
    assert insufficient[0] == "No Signal"
    assert insufficient[1] is None and insufficient[2] is None
    assert insufficient[5] is False
    assert "Insufficient synchronized history" in insufficient[8]

    missing_liquidity = service.classify_relative_value_state(
        spread=100.0, rolling_mean=20.0, z_score=2.2, percentile=96.0,
        dte_min=20, min_volume=None, min_open_interest=5000, cost_hurdle=25.0
    )
    assert missing_liquidity[0] == "Watch"
    assert missing_liquidity[5] is False
    assert "liquidity is unassessed" in missing_liquidity[8]


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
        assert p["deviation_intensity"] is None or 0.0 <= p["deviation_intensity"] <= 100.0
        assert p["classification"] in ("Investigate", "Watch", "Cost-Blocked", "Expiry-Risk", "No Signal")
        if (p["snapshot_freshness"] == "future-dated" or (p["data_age_days"] is not None and p["data_age_days"] > 3)) and p["spread"] is not None:
            # Old/future snapshots may retain historical metrics but cannot expose
            # current actionable scores from the default/latest radar.
            assert p["classification"] == "No Signal"
            assert p["opportunity_score"] is None
            assert p["trap_risk_score"] is None
            assert p["gross_edge"] is None
            assert p["net_edge"] is None
            assert "scoring suppressed" in p["reason"].lower()
        else:
            assert p["opportunity_score"] is None or 0.0 <= p["opportunity_score"] <= 100.0
            assert p["trap_risk_score"] is None or 0.0 <= p["trap_risk_score"] <= 100.0
        if p["spread"] is not None:
            assert p["trade_date"] == data["evaluation_date"]
            assert p["expiry_date"] == "2026-10-30"
            assert p["historical_norm"] is None or 0 <= p["historical_norm"] <= 100
            assert p["friction_boundary"] is None or 0 <= p["friction_boundary"] <= 100


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

    # IDs are used as the Market Detective selector key, so same-date events
    # for different GOLD* pairs must remain distinct.
    ids = [event["event_id"] for event in data["items"]]
    assert len(ids) == len(set(ids))
    for event in data["items"]:
        assert f"-{event['pair']}-" in event["event_id"]


def test_event_ids_remain_unique_across_gold_pairs(db_session: Session):
    """Market Detective uses event_id as a key; GOLD* prefixes must not collide."""
    csv_path = os.path.join(SAMPLE_DIR, "sample_mcx_gold_bhavcopy_valid.csv")
    with open(csv_path, "rb") as source:
        file_bytes = source.read()
    file_bytes = file_bytes.replace(b"2026-11-27", b"2026-10-30").replace(b"2026-10-28", b"2026-10-30")
    CsvIngestionService(db_session).process_csv(
        file_bytes=file_bytes,
        filename="event-id-regression.csv",
        data_source="csv_upload",
        is_synthetic=False,
    )

    events = RelativeValueAnalyticsService(db_session).get_events(limit=200)
    event_ids = [event.event_id for event in events.items]
    assert len(event_ids) == len(set(event_ids))
    assert all(f"-{event.pair}-" in event.event_id for event in events.items)


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
    assert data["evaluation_date"] == "2026-10-15"
    assert data["expiry_date"] == "2026-10-30"
    assert data["current_spread"] is not None
    assert data["current_z_score"] is not None


def test_distribution_uses_at_most_requested_synchronized_observations(client, db_session):
    ingest_sample_bhavcopy(client)
    service = RelativeValueAnalyticsService(db_session)
    result = service.get_spread_distribution("GOLDM-GOLDPETAL", window_days=2, num_bins=5)
    series = service.calculate_pairwise_spread_series("GOLDM", "GOLDPETAL", window_days=2)
    expected = series.data_points[-2:]

    assert result.sample_size == 2
    assert result.mean == round(sum(point.spread for point in expected) / 2, 2)
    assert result.current_spread == expected[-1].spread
    assert result.evaluation_date == expected[-1].trade_date
    assert result.expiry_date == expected[-1].expiry_date
    assert result.current_z_score.startswith(f"{expected[-1].z_score:+.2f}σ")


def test_radar_unavailable_pair_explains_expiry_mismatch(client):
    csv_content = (
        b"symbol,trade_date,expiry_date,close\n"
        b"GOLDM,2026-10-21,2026-11-05,62000\n"
        b"GOLDPETAL,2026-10-21,2026-10-30,6250\n"
    )
    upload = client.post(
        "/api/data/upload",
        files={"file": ("expiry_mismatch.csv", io.BytesIO(csv_content), "text/csv")},
        data={"data_source": "csv_upload", "is_synthetic": "false"},
    )
    assert upload.status_code == 200
    radar = client.get("/api/analytics/radar?window=30").json()["data"]
    pair = next(row for row in radar["pairs"] if row["pair"] == "GOLDM-GOLDPETAL")

    assert pair["spread"] is None
    assert "2026-10-21" in pair["reason"]
    assert "GOLDM expiries: 2026-11-05" in pair["reason"]
    assert "GOLDPETAL expiries: 2026-10-30" in pair["reason"]
    assert "Different expiries are not paired" in pair["reason"]


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


def test_synchronized_pairs_require_same_expiry_on_same_trade_date(db_session: Session):
    service = RelativeValueAnalyticsService(db_session)
    trade_day = date(2026, 12, 1)
    monthly = date(2026, 12, 28)
    next_month = date(2027, 1, 25)
    db_session.add_all([
        MarketObservation(symbol="GOLDM", trade_date=trade_day, expiry_date=monthly,
            close_price=62000, normalized_price_per_gram=6200, normalized_price_10g_basis=62000),
        MarketObservation(symbol="GOLDM", trade_date=trade_day, expiry_date=next_month,
            close_price=63000, normalized_price_per_gram=6300, normalized_price_10g_basis=63000),
        MarketObservation(symbol="GOLDPETAL", trade_date=trade_day, expiry_date=monthly,
            close_price=62000, normalized_price_per_gram=6200, normalized_price_10g_basis=62000),
        MarketObservation(symbol="GOLDPETAL", trade_date=trade_day, expiry_date=next_month,
            close_price=63000, normalized_price_per_gram=6300, normalized_price_10g_basis=63000),
    ])
    db_session.commit()

    pairs = service.get_synchronized_observations("GOLDM", "GOLDPETAL")
    assert len(pairs) == 1
    assert pairs[0][0].expiry_date == pairs[0][1].expiry_date == monthly


def test_same_trade_date_with_no_shared_expiry_is_not_a_pair(db_session: Session):
    service = RelativeValueAnalyticsService(db_session)
    trade_day = date(2026, 12, 2)
    db_session.add_all([
        MarketObservation(symbol="GOLDM", trade_date=trade_day, expiry_date=date(2026, 12, 28),
            close_price=62000, normalized_price_per_gram=6200, normalized_price_10g_basis=62000),
        MarketObservation(symbol="GOLDPETAL", trade_date=trade_day, expiry_date=date(2027, 1, 25),
            close_price=6200, normalized_price_per_gram=6200, normalized_price_10g_basis=62000),
    ])
    db_session.commit()
    assert service.get_synchronized_observations("GOLDM", "GOLDPETAL") == []


def test_pairwise_spread_matches_independent_fine_gold_995_calculation_and_is_antisymmetric(db_session: Session):
    service = RelativeValueAnalyticsService(db_session)
    trade_day = date(2026, 12, 1)
    expiry = date(2026, 12, 30)
    goldten_quote = 145015.0  # ₹ per 10g, 999 purity
    guinea_quote = 116648.0   # ₹ per 8g, 999 purity

    # Independently apply the documented benchmark equation: (quote / quote grams / purity) * 10g * 995/1000.
    goldten_basis = round((goldten_quote / 10.0 / 0.999) * 10.0 * 0.995, 2)
    guinea_basis = round((guinea_quote / 8.0 / 0.999) * 10.0 * 0.995, 2)
    db_session.add_all([
        MarketObservation(symbol="GOLDTEN", trade_date=trade_day, expiry_date=expiry,
            close_price=goldten_quote, normalized_price_per_gram=goldten_basis / 9.95,
            normalized_price_10g_basis=goldten_basis),
        MarketObservation(symbol="GOLDGUINEA", trade_date=trade_day, expiry_date=expiry,
            close_price=guinea_quote, normalized_price_per_gram=guinea_basis / 9.95,
            normalized_price_10g_basis=guinea_basis),
    ])
    db_session.commit()

    expected = round(
        (goldten_quote / 10.0 / 0.999 * 10.0 * 0.995) -
        (guinea_quote / 8.0 / 0.999 * 10.0 * 0.995),
        2,
    )
    forward = service.calculate_pairwise_spread_series("GOLDTEN", "GOLDGUINEA").data_points[-1]
    reverse = service.calculate_pairwise_spread_series("GOLDGUINEA", "GOLDTEN").data_points[-1]

    assert forward.spread == expected == -791.82
    assert reverse.spread == -expected == 791.82
    assert forward.trade_date == reverse.trade_date == trade_day
    assert forward.expiry_date == reverse.expiry_date == expiry


def test_distribution_documents_same_expiry_per_point_and_front_expiry_roll(db_session: Session):
    service = RelativeValueAnalyticsService(db_session)
    rows = []
    sessions = [
        (date(2026, 12, 1), date(2026, 12, 30)),
        (date(2026, 12, 1), date(2027, 1, 27)),  # multiple shared expiries: front one is selected
        (date(2027, 1, 4), date(2027, 1, 27)),   # following session uses the next listed expiry
    ]
    for trade_day, expiry in sessions:
        price_a = 62000.0 if expiry.month == 12 else 63000.0
        price_b = price_a - 100.0
        rows.extend([
            MarketObservation(symbol="GOLDTEN", trade_date=trade_day, expiry_date=expiry,
                close_price=price_a, normalized_price_per_gram=price_a / 10,
                normalized_price_10g_basis=price_a),
            MarketObservation(symbol="GOLDGUINEA", trade_date=trade_day, expiry_date=expiry,
                close_price=price_b / 10 * 8, normalized_price_per_gram=price_b / 10,
                normalized_price_10g_basis=price_b),
        ])
    db_session.add_all(rows)
    db_session.commit()

    synchronized = service.get_synchronized_observations("GOLDTEN", "GOLDGUINEA")
    assert [(a.trade_date, a.expiry_date, b.expiry_date) for a, b in synchronized] == [
        (date(2026, 12, 1), date(2026, 12, 30), date(2026, 12, 30)),
        (date(2027, 1, 4), date(2027, 1, 27), date(2027, 1, 27)),
    ]

    distribution = service.get_spread_distribution("GOLDTEN-GOLDGUINEA", window_days=365)
    assert distribution.sample_size == 2
    assert distribution.evaluation_date == date(2027, 1, 4)
    assert distribution.expiry_date == date(2027, 1, 27)
    assert "same trade date and expiry" in distribution.expiry_policy
    assert "expiry can roll across history" in distribution.expiry_policy


def test_test_only_observations_do_not_create_radar_or_distribution_results(client, db_session):
    trade_day = date(2026, 10, 20)
    expiry = date(2026, 10, 30)
    db_session.add_all([
        MarketObservation(symbol="GOLDM", trade_date=trade_day, expiry_date=expiry,
            close_price=62000, normalized_price_per_gram=6200, normalized_price_10g_basis=62000,
            data_source="test_run"),
        MarketObservation(symbol="GOLDPETAL", trade_date=trade_day, expiry_date=expiry,
            close_price=62000, normalized_price_per_gram=6200, normalized_price_10g_basis=62000,
            data_source="test_invalid"),
    ])
    db_session.commit()

    radar = client.get("/api/analytics/radar?window=30")
    assert radar.status_code == 200
    pairs = radar.json()["data"]["pairs"]
    assert len(pairs) == 6
    assert all(pair["spread"] is None and pair["trade_date"] is None for pair in pairs)
    assert all(pair["classification"] == "No Signal" for pair in pairs)
    assert all(pair["min_volume"] is None and pair["min_open_interest"] is None for pair in pairs)
    assert all(pair["is_liquidity_trap"] is False for pair in pairs)
    assert all(pair["opportunity_score"] is None and pair["trap_risk_score"] is None for pair in pairs)
    assert all(pair["deviation_intensity"] is None for pair in pairs)

    distribution = client.get("/api/analytics/distribution?pair=GOLDM-GOLDPETAL&window=365")
    assert distribution.status_code == 200
    assert distribution.json()["data"]["sample_size"] == 0
    assert db_session.query(MarketObservation).count() == 2  # retained for audit


def test_synthetic_observations_do_not_create_radar_events_or_distribution(client, db_session):
    trade_day = date(2026, 10, 20)
    expiry = date(2026, 10, 30)
    db_session.add_all([
        MarketObservation(symbol="GOLDM", trade_date=trade_day, expiry_date=expiry,
            close_price=62000, normalized_price_per_gram=6200, normalized_price_10g_basis=62000,
            data_source="synthetic_seed", is_synthetic=True),
        MarketObservation(symbol="GOLDPETAL", trade_date=trade_day, expiry_date=expiry,
            close_price=61000, normalized_price_per_gram=6100, normalized_price_10g_basis=61000,
            data_source="synthetic_seed", is_synthetic=True),
    ])
    db_session.commit()

    radar = client.get("/api/analytics/radar?window=30").json()["data"]
    events = client.get("/api/analytics/events?limit=30").json()["data"]
    distribution = client.get("/api/analytics/distribution?pair=GOLDM-GOLDPETAL&window=365").json()["data"]

    assert radar["evaluation_date"] is None
    assert all(pair["spread"] is None and pair["classification"] == "No Signal" for pair in radar["pairs"])
    assert all(pair["is_liquidity_trap"] is False and pair["min_volume"] is None for pair in radar["pairs"])
    assert events["total_events"] == 0 and events["items"] == []
    assert distribution["sample_size"] == 0
    assert db_session.query(MarketObservation).count() == 2  # retained for audit


def test_imported_csv_is_eligible_and_lowercase_canonical_symbols_are_normalized(client, db_session):
    csv_content = (
        b"symbol,trade_date,expiry_date,close,volume,open_interest\n"
        b"goldm,2026-10-20,2026-10-30,62000,1000,9000\n"
        b"goldpetal,2026-10-20,2026-10-30,6250,300,1500\n"
        b"goldm,2026-10-21,2026-10-30,62100,1100,9100\n"
        b"goldpetal,2026-10-21,2026-10-30,6260,320,1510\n"
    )
    upload = client.post(
        "/api/data/upload",
        files={"file": ("legitimate_import.csv", io.BytesIO(csv_content), "text/csv")},
        data={"data_source": "csv_upload", "is_synthetic": "false"},
    )
    assert upload.status_code == 200 and upload.json()["data"]["accepted_rows"] == 4
    assert {row.symbol for row in db_session.query(MarketObservation).all()} == {"GOLDM", "GOLDPETAL"}
    assert all(row.volume_observed and row.open_interest_observed for row in db_session.query(MarketObservation).all())

    radar = client.get("/api/analytics/radar?window=30").json()["data"]
    pair = next(row for row in radar["pairs"] if row["pair"] == "GOLDM-GOLDPETAL")
    assert radar["evaluation_date"] == "2026-10-21"
    assert pair["trade_date"] == radar["evaluation_date"]
    assert pair["expiry_date"] == "2026-10-30"
    assert pair["spread"] is not None and pair["z_score"] is not None
    assert pair["min_volume"] == 320
    assert pair["min_open_interest"] == 1510


def test_missing_volume_or_oi_is_null_and_not_a_liquidity_trap(client):
    csv_content = (
        b"symbol,trade_date,expiry_date,close\n"
        b"GOLDM,2026-10-20,2026-10-30,62000\n"
        b"GOLDPETAL,2026-10-20,2026-10-30,6250\n"
        b"GOLDM,2026-10-21,2026-10-30,62100\n"
        b"GOLDPETAL,2026-10-21,2026-10-30,6260\n"
    )
    upload = client.post(
        "/api/data/upload",
        files={"file": ("missing_liquidity_fields.csv", io.BytesIO(csv_content), "text/csv")},
        data={"data_source": "csv_upload", "is_synthetic": "false"},
    )
    assert upload.status_code == 200 and upload.json()["data"]["accepted_rows"] == 4

    radar = client.get("/api/analytics/radar?window=30").json()["data"]
    pair = next(row for row in radar["pairs"] if row["pair"] == "GOLDM-GOLDPETAL")
    assert pair["spread"] is not None
    assert pair["min_volume"] is None and pair["min_open_interest"] is None
    assert pair["is_liquidity_trap"] is False
    assert "liquidity is unassessed" in pair["reason"].lower()
    series = client.get("/api/analytics/spreads?pair=GOLDM-GOLDPETAL&window=30").json()["data"]
    assert series["data_points"][-1]["volume_a"] is None
    assert series["data_points"][-1]["open_interest_b"] is None


def test_explicit_zero_volume_remains_a_real_zero(client):
    csv_content = (
        b"symbol,trade_date,expiry_date,close,volume,open_interest\n"
        b"GOLDM,2026-10-20,2026-10-30,62000,0,9000\n"
        b"GOLDPETAL,2026-10-20,2026-10-30,6250,300,1500\n"
        b"GOLDM,2026-10-21,2026-10-30,62100,0,9100\n"
        b"GOLDPETAL,2026-10-21,2026-10-30,6260,320,1510\n"
    )
    upload = client.post(
        "/api/data/upload",
        files={"file": ("explicit_zero_volume.csv", io.BytesIO(csv_content), "text/csv")},
        data={"data_source": "csv_upload", "is_synthetic": "false"},
    )
    assert upload.status_code == 200 and upload.json()["data"]["accepted_rows"] == 4
    pair = next(row for row in client.get("/api/analytics/radar?window=30").json()["data"]["pairs"]
                if row["pair"] == "GOLDM-GOLDPETAL")
    assert pair["min_volume"] == 0
    assert pair["min_open_interest"] == 1510
    assert pair["is_liquidity_trap"] is True


def test_empty_market_and_radar_apis_return_no_observations(client):
    prices = client.get("/api/market/prices")
    assert prices.status_code == 200
    assert prices.json()["data"]["items"] == []
    assert prices.json()["data"]["pagination"]["total"] == 0

    radar = client.get("/api/analytics/radar")
    assert radar.status_code == 200
    assert radar.json()["data"]["evaluation_date"] is None
    assert all(pair["spread"] is None for pair in radar.json()["data"]["pairs"])
    assert all(pair["min_volume"] is None and pair["min_open_interest"] is None for pair in radar.json()["data"]["pairs"])
    assert all(pair["is_liquidity_trap"] is False for pair in radar.json()["data"]["pairs"])


def test_radar_baseline_visuals_are_not_fabricated_without_history(client, db_session):
    day = date(2026, 10, 20)
    expiry = date(2026, 10, 30)
    db_session.add_all([
        MarketObservation(symbol="GOLDM", trade_date=day, expiry_date=expiry,
            close_price=62000, normalized_price_per_gram=6200, normalized_price_10g_basis=62000),
        MarketObservation(symbol="GOLDPETAL", trade_date=day, expiry_date=expiry,
            close_price=61900, normalized_price_per_gram=6190, normalized_price_10g_basis=61900),
    ])
    db_session.commit()

    response = client.get("/api/analytics/radar")
    assert response.status_code == 200
    pair = next(item for item in response.json()["data"]["pairs"] if item["pair"] == "GOLDM-GOLDPETAL")
    assert pair["spread"] == 100
    assert pair["historical_norm"] is None
    assert pair["friction_boundary"] is None


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



def test_pairwise_spreads_are_transitive_on_same_session_and_expiry(client):
    """Pair spreads must reconcile when all legs share the same session/expiry.

    For normalized prices A, B, C: (A-B) + (B-C) == (A-C).
    This protects the radar from pair cards that disagree because of mismatched
    observations or inconsistent normalization.
    """
    ingest_sample_bhavcopy(client)

    pair_names = (
        "GOLDTEN-GOLDGUINEA",
        "GOLDGUINEA-GOLDPETAL",
        "GOLDTEN-GOLDPETAL",
    )
    snapshots = {}
    for pair_name in pair_names:
        response = client.get(f"/api/analytics/spreads?pair={pair_name}&window=30")
        assert response.status_code == 200
        points = response.json()["data"]["data_points"]
        snapshots[pair_name] = {point["trade_date"]: point for point in points}

    common_dates = (
        set(snapshots[pair_names[0]])
        & set(snapshots[pair_names[1]])
        & set(snapshots[pair_names[2]])
    )
    assert common_dates, "sample fixture must contain a synchronized three-leg session"

    for trade_date in common_dates:
        ten_guinea = snapshots["GOLDTEN-GOLDGUINEA"][trade_date]
        guinea_petal = snapshots["GOLDGUINEA-GOLDPETAL"][trade_date]
        ten_petal = snapshots["GOLDTEN-GOLDPETAL"][trade_date]

        assert ten_guinea["expiry_date"] == guinea_petal["expiry_date"] == ten_petal["expiry_date"]
        assert abs(
            (ten_guinea["spread"] + guinea_petal["spread"]) - ten_petal["spread"]
        ) < 0.02


def test_event_evidence_preserves_unobserved_liquidity_as_unavailable():
    evidence = EventEvidenceTrail(
        spread=-100.0,
        cost_hurdle=25.31,
        rule_triggered="Liquidity unassessed",
        volume_a=None,
        volume_b=None,
        open_interest_a=None,
        open_interest_b=None,
    )

    assert evidence.volume_a is None
    assert evidence.volume_b is None
    assert evidence.open_interest_a is None
    assert evidence.open_interest_b is None


def test_event_evidence_preserves_observed_zero_liquidity():
    evidence = EventEvidenceTrail(
        spread=-100.0,
        cost_hurdle=25.31,
        rule_triggered="Observed zero volume",
        volume_a=0,
        volume_b=12,
        open_interest_a=0,
        open_interest_b=5,
    )

    assert evidence.volume_a == 0
    assert evidence.volume_b == 12
    assert evidence.open_interest_a == 0
    assert evidence.open_interest_b == 5
