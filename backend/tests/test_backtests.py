from datetime import date, timedelta
import pytest

from backend.app.models.market_observation import MarketObservation
from backend.app.models.data_import import ImportBatch
from backend.app.schemas.backtest import BacktestRequest
from backend.app.services.backtest_service import BacktestService


def test_default_backtest_fees_exclude_separately_configured_slippage():
    request = BacktestRequest()

    # Analytics' reference round-trip hurdle is ₹25.31/10g including ₹15 slippage.
    # Backtesting accepts fees and slippage separately, so its fee default must be ₹10.31.
    assert request.transaction_cost_per_10g == pytest.approx(10.31)
    assert request.slippage_per_10g == pytest.approx(15.00)
    assert request.transaction_cost_per_10g + request.slippage_per_10g == pytest.approx(25.31)


def test_backtest_excludes_synthetic_rows(db_session):
    for idx in range(8):
        day = date(2026, 1, 1) + timedelta(days=idx)
        for symbol, value in (("GOLDM", 62500 + idx), ("GOLDPETAL", 62400)):
            db_session.add(MarketObservation(
                symbol=symbol, trade_date=day, expiry_date=day + timedelta(days=25),
                close_price=value, normalized_price_per_gram=value / 10,
                normalized_price_10g_basis=value, volume=1000, open_interest=1000,
                data_source="synthetic_seed", is_synthetic=True,
            ))
    db_session.commit()

    result = BacktestService(db_session).run(BacktestRequest(pair="GOLDM-GOLDPETAL", lookback=5))
    assert result.status == "no_eligible_data"
    assert result.observations == 0
    assert result.metrics.total_return_pct is None
    assert result.trades == []


def test_backtest_pairs_only_matching_expiries_on_same_date(db_session):
    day = date(2026, 5, 1)
    monthly = date(2026, 5, 28)
    next_month = date(2026, 6, 25)
    db_session.add_all([
        MarketObservation(symbol="GOLDM", trade_date=day, expiry_date=monthly,
            close_price=62500, normalized_price_per_gram=6250, normalized_price_10g_basis=62500,
            data_source="csv_upload", is_synthetic=False),
        MarketObservation(symbol="GOLDM", trade_date=day, expiry_date=next_month,
            close_price=63500, normalized_price_per_gram=6350, normalized_price_10g_basis=63500,
            data_source="csv_upload", is_synthetic=False),
        MarketObservation(symbol="GOLDPETAL", trade_date=day, expiry_date=monthly,
            close_price=62500, normalized_price_per_gram=6250, normalized_price_10g_basis=62500,
            data_source="csv_upload", is_synthetic=False),
    ])
    db_session.commit()

    pairs = BacktestService(db_session)._paired_rows(BacktestRequest(pair="GOLDM-GOLDPETAL", lookback=5))
    assert len(pairs) == 1
    assert pairs[0][0].expiry_date == pairs[0][1].expiry_date == monthly


def test_backtest_excludes_test_invalid_source_and_test_import_batch(db_session):
    day = date(2026, 6, 1)
    batches = []
    for source in ("test_invalid", "test_run"):
        batch = ImportBatch(filename=f"{source}.csv", file_hash=(source + "0" * 64)[:64],
            data_source=source, is_synthetic=False)
        db_session.add(batch)
        batches.append(batch)
    db_session.flush()
    for symbol, batch in zip(("GOLDM", "GOLDPETAL"), batches):
        db_session.add(MarketObservation(
            symbol=symbol, trade_date=day, expiry_date=date(2026, 6, 28),
            close_price=62500, normalized_price_per_gram=6250, normalized_price_10g_basis=62500,
            data_source="csv_upload", is_synthetic=False, import_batch_id=batch.id,
        ))
    db_session.commit()

    result = BacktestService(db_session).run(BacktestRequest(pair="GOLDM-GOLDPETAL", lookback=5))
    assert result.status == "no_eligible_data"
    assert result.observations == 0


def test_backtest_reports_insufficient_real_history(db_session):
    for idx in range(8):
        day = date(2026, 2, 1) + timedelta(days=idx)
        spread = [0, 8, -4, 12, -9, 3, -2, 7][idx]
        for symbol, value in (("GOLDM", 62500 + spread), ("GOLDPETAL", 62500)):
            db_session.add(MarketObservation(
                symbol=symbol, trade_date=day, expiry_date=day + timedelta(days=25),
                close_price=value, normalized_price_per_gram=value / 10,
                normalized_price_10g_basis=value, volume=1000, open_interest=1000,
                data_source="csv_upload", is_synthetic=False,
            ))
    db_session.commit()

    result = BacktestService(db_session).run(BacktestRequest(pair="GOLDM-GOLDPETAL", lookback=10))
    assert result.status == "insufficient_history"
    assert result.observations == 8
    assert result.first_date == date(2026, 2, 1)
    assert result.last_date == date(2026, 2, 8)


def test_backtest_runs_on_eligible_observations(db_session):
    spreads = [0, 2, -2, 3, -3, 4, -4, 5, -5, 1, 0, -1, 2, -2, 4, -4, 0, 1]
    for idx, spread in enumerate(spreads):
        day = date(2026, 3, 1) + timedelta(days=idx)
        for symbol, value in (("GOLDM", 62500 + spread), ("GOLDPETAL", 62500)):
            db_session.add(MarketObservation(
                symbol=symbol, trade_date=day, expiry_date=day + timedelta(days=25),
                close_price=value, normalized_price_per_gram=value / 10,
                normalized_price_10g_basis=value, volume=1000, open_interest=1000,
                volume_observed=True,
                data_source="csv_upload", is_synthetic=False,
            ))
    db_session.commit()

    req = BacktestRequest(pair="GOLDM-GOLDPETAL", lookback=5, entry_z=1.0, exit_z=0.2, units=3)
    result = BacktestService(db_session).run(req)
    assert result.status == "completed"
    assert result.observations == len(spreads)
    assert len(result.equity_curve) == len(spreads)
    assert result.metrics.total_trades > 0
    assert all(trade.units == 3 for trade in result.trades)
    assert result.metrics.total_costs is not None
    assert abs(result.metrics.total_pnl - (result.equity_curve[-1].equity - req.capital)) < 0.01


@pytest.mark.parametrize(
    ("volume", "observed", "min_volume", "expected_trades"),
    [
        (0, False, 0, 0),       # missing volume is not observed zero
        (0, False, 10, 0),      # same safety gate with a positive threshold
        (-1, True, 0, 0),       # observed values must still be nonnegative
        (0, True, 0, 2),        # observed zero satisfies the configured zero threshold
        (5, True, 6, 0),        # observed but below threshold
        (6, True, 6, 2),        # threshold is inclusive
        (7, True, 6, 2),        # above threshold
    ],
)
def test_backtest_requires_observed_volume_and_preserves_threshold_semantics(
    db_session, volume, observed, min_volume, expected_trades,
):
    spreads = [0, 2, -2, 3, -3, 4, -4, 5, -5, 1, 0, -1, 2, -2, 4, -4, 0, 1]
    for idx, spread in enumerate(spreads):
        day = date(2026, 7, 1) + timedelta(days=idx)
        # Keep one contract expiry across the historical window; a changing
        # expiry every day would correctly trigger the engine expiry-roll guard.
        expiry = date(2026, 8, 25)
        for symbol, close in (("GOLDM", 62500 + spread), ("GOLDPETAL", 62500)):
            db_session.add(MarketObservation(
                symbol=symbol, trade_date=day, expiry_date=expiry,
                close_price=close, normalized_price_per_gram=close / 10,
                normalized_price_10g_basis=close, volume=volume, volume_observed=observed,
                data_source="csv_upload", is_synthetic=False,
            ))
    db_session.commit()

    result = BacktestService(db_session).run(BacktestRequest(
        pair="GOLDM-GOLDPETAL", lookback=5, entry_z=1.0, exit_z=0.2,
        min_volume=min_volume,
    ))

    assert result.status == "completed"
    assert result.metrics.total_trades == expected_trades


def test_backtest_api_returns_truthful_empty_state_for_sample_csv(client):
    response = client.post("/api/backtests/run", json={"pair": "GOLDM-GOLDPETAL", "lookback": 5})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "no_eligible_data"
    assert body["data"]["metrics"]["total_return_pct"] is None
    assert body["data"]["equity_curve"] == []


def test_backtest_api_validates_strategy_thresholds(client):
    response = client.post("/api/backtests/run", json={"entry_z": 1.0, "exit_z": 1.0})
    assert response.status_code == 422


def test_backtest_api_runs_full_request_with_real_rows(client, db_session):
    spreads = [0, 2, -2, 3, -3, 4, -4, 5, -5, 1, 0, -1, 2, -2, 4, -4, 0, 1]
    for idx, spread in enumerate(spreads):
        day = date(2026, 4, 1) + timedelta(days=idx)
        for symbol, close in (("GOLDM", 62500 + spread), ("GOLDPETAL", 62500)):
            db_session.add(MarketObservation(
                symbol=symbol, trade_date=day, expiry_date=day + timedelta(days=25),
                close_price=close, normalized_price_per_gram=close / 10,
                normalized_price_10g_basis=close, volume=1000, open_interest=1000,
                data_source="csv_upload", is_synthetic=False,
            ))
    db_session.commit()

    response = client.post("/api/backtests/run", json={
        "pair": "GOLDM-GOLDPETAL", "lookback": 5, "entry_z": 1.0,
        "exit_z": 0.2, "units": 2, "capital": 250000,
    })
    assert response.status_code == 200
    result = response.json()["data"]
    assert result["status"] == "completed"
    assert result["observations"] == len(spreads)
    assert result["metrics"]["total_pnl"] == round(result["equity_curve"][-1]["equity"] - 250000, 2)
    assert all(trade["units"] == 2 for trade in result["trades"])


def test_backtest_uses_only_nearest_shared_expiry_per_session(db_session):
    day = date(2026, 5, 4)
    front_expiry = date(2026, 5, 28)
    next_expiry = date(2026, 6, 25)
    db_session.add_all([
        MarketObservation(
            symbol="GOLDM", trade_date=day, expiry_date=next_expiry,
            close_price=63500, normalized_price_per_gram=6350,
            normalized_price_10g_basis=63500, data_source="csv_upload", is_synthetic=False,
        ),
        MarketObservation(
            symbol="GOLDM", trade_date=day, expiry_date=front_expiry,
            close_price=62500, normalized_price_per_gram=6250,
            normalized_price_10g_basis=62500, data_source="csv_upload", is_synthetic=False,
        ),
        MarketObservation(
            symbol="GOLDPETAL", trade_date=day, expiry_date=next_expiry,
            close_price=63400, normalized_price_per_gram=6340,
            normalized_price_10g_basis=63400, data_source="csv_upload", is_synthetic=False,
        ),
        MarketObservation(
            symbol="GOLDPETAL", trade_date=day, expiry_date=front_expiry,
            close_price=62400, normalized_price_per_gram=6240,
            normalized_price_10g_basis=62400, data_source="csv_upload", is_synthetic=False,
        ),
    ])
    db_session.commit()

    pairs = BacktestService(db_session)._paired_rows(
        BacktestRequest(pair="GOLDM-GOLDPETAL", lookback=5)
    )

    assert len(pairs) == 1
    assert pairs[0][0].trade_date == day
    assert pairs[0][0].expiry_date == pairs[0][1].expiry_date == front_expiry
    assert pairs[0][2] == 100
