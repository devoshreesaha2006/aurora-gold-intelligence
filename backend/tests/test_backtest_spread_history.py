"""Regression coverage for backtest contract-expiry rolls."""
from datetime import date, timedelta

import pytest

from backend.app.models.market_observation import MarketObservation
from backend.app.schemas.backtest import BacktestRequest
from backend.app.services.backtest_service import BacktestService


def _add_pair(db, day, expiry, spread, base=62500):
    for symbol, value in (("GOLDM", base + spread), ("GOLDPETAL", base)):
        db.add(MarketObservation(
            symbol=symbol, trade_date=day, expiry_date=expiry, close_price=value,
            normalized_price_per_gram=value / 10, normalized_price_10g_basis=value,
            volume=1000, open_interest=1, volume_observed=True,
            data_source="csv_upload", is_synthetic=False,
        ))


def test_expiry_roll_never_books_cross_contract_level_jump_as_pnl(db_session):
    """The new pair's level must not be booked as a tradable spread move."""
    march, april = date(2026, 3, 15), date(2026, 4, 12)
    start = date(2026, 3, 1)
    quiet = [100, 101, 99, 100, 101, 99, 100, 101, 99, 100, 101, 99]
    for i, spread in enumerate(quiet + [140, 140, 140]):
        _add_pair(db_session, start + timedelta(days=i), march, spread)
    for j in range(5):
        _add_pair(db_session, start + timedelta(days=15 + j), april, 180)
    db_session.commit()

    req = BacktestRequest(
        pair="GOLDM-GOLDPETAL", lookback=10, entry_z=2.0, exit_z=0.5,
        expiry_buffer_days=0, transaction_cost_per_10g=0, slippage_per_10g=0,
    )
    result = BacktestService(db_session).run(req)

    assert result.trades
    first = result.trades[0]
    assert first.entry_date == date(2026, 3, 14)
    assert first.direction == "Short spread"
    assert first.exit_reason.startswith("Expiry roll")
    assert first.exit_date == date(2026, 3, 15)
    assert first.exit_spread == pytest.approx(140.0)
    assert first.gross_pnl == pytest.approx(0.0)
    assert result.metrics.gross_pnl == pytest.approx(sum(t.gross_pnl for t in result.trades))
    assert result.metrics.total_pnl == pytest.approx(sum(t.net_pnl for t in result.trades), abs=0.01)
