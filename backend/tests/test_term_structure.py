from datetime import date

from backend.app.models.market_observation import MarketObservation
from backend.app.services.term_structure_service import TermStructureService


def _add_pair_rows(db_session, day, expiry, spread):
    for symbol, normalized in (("GOLDM", 62500 + spread), ("GOLDPETAL", 62500)):
        db_session.add(MarketObservation(
            symbol=symbol,
            trade_date=day,
            expiry_date=expiry,
            close_price=normalized,
            normalized_price_per_gram=normalized / 10,
            normalized_price_10g_basis=normalized,
            volume=100,
            open_interest=100,
            volume_observed=True,
            open_interest_observed=True,
            data_source="csv_upload",
            is_synthetic=False,
        ))


def test_term_structure_separates_same_expiry_change_from_front_switch_gap(db_session):
    june = date(2026, 6, 30)
    july = date(2026, 7, 30)
    _add_pair_rows(db_session, date(2026, 6, 1), june, 100)
    _add_pair_rows(db_session, date(2026, 6, 2), june, 110)
    _add_pair_rows(db_session, date(2026, 6, 2), july, 190)
    _add_pair_rows(db_session, date(2026, 6, 3), july, 200)
    db_session.commit()

    report = TermStructureService(db_session).report("GOLDM-GOLDPETAL")

    assert report["status"] == "available"
    assert report["observations"] == 3
    assert report["front_series"][1]["front_same_expiry_change"] == 10
    assert report["front_series"][2]["front_same_expiry_change"] is None
    # The old expiry is absent on the switch date, so a same-session roll gap
    # is not identifiable; yesterday-vs-today would mix market movement and roll.
    assert report["front_series"][2]["front_switch_gap"] is None
    assert report["front_series"][2]["front_switch_gap_available"] is False
    assert report["front_series"][2]["front_expiry_changed"] is True
    assert report["decomposition"]["front_expiry_switch_count"] == 1
    assert report["decomposition"]["measurable_front_switch_gap_count"] == 0
    assert report["decomposition"]["cumulative_front_switch_gaps"] == 0
    assert report["carry_model"]["status"] == "unavailable"
    assert report["lifecycle_validation"]["tender_period_validation"].startswith("unavailable")
    assert report["lifecycle_validation"]["effective_dated_contract_specifications"] is False
    assert report["data_quality"]["verified_bid_ask_data"] is False


def test_term_structure_accepts_reversed_pair_direction(db_session):
    _add_pair_rows(db_session, date(2026, 6, 1), date(2026, 6, 30), 125)
    db_session.commit()

    report = TermStructureService(db_session).report("GOLDPETAL-GOLDM")
    point = report["front_series"][0]
    assert report["pair"] == "GOLDPETAL-GOLDM"
    assert point["spread"] == -125
    assert point["price_a"] == 62500
    assert point["price_b"] == 62625
