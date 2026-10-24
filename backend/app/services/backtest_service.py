"""Historical, close-to-close mean-reversion simulation for normalized gold spreads."""
from datetime import date
from math import isfinite, sqrt
from statistics import mean, stdev
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.models.data_import import ImportBatch
from backend.app.models.market_observation import MarketObservation
from backend.app.services.data_provenance import is_synthetic_source, is_test_source
from backend.app.schemas.backtest import (
    BacktestMetricSet, BacktestRequest, BacktestResponse, BacktestTrade, EquityPoint, SpreadPoint,
)


ASSUMPTIONS = [
    "Signals use trailing spread statistics available at the prior settlement; execution is modeled at the next settlement.",
    "Spread P&L uses normalized ₹ per 10g basis and the configured number of spread units.",
    "Configured transaction cost and slippage are charged half on entry and half on exit per 10g unit.",
    "Only synchronized, non-synthetic observations from non-test imports are eligible; settlement fills are proxies, not executable quotes.",
]


class BacktestService:
    def __init__(self, db: Session):
        self.db = db

    def _eligible_rows(self, symbol: str, start: Optional[date], end: Optional[date]):
        query = self.db.query(MarketObservation).filter(
            MarketObservation.symbol == symbol,
            MarketObservation.is_synthetic.is_(False),
        )
        if start:
            query = query.filter(MarketObservation.trade_date >= start)
        if end:
            query = query.filter(MarketObservation.trade_date <= end)
        rows = query.order_by(MarketObservation.trade_date.asc()).all()
        eligible = []
        for row in rows:
            source = row.data_source
            if is_test_source(source) or is_synthetic_source(source):
                continue
            if row.import_batch_id:
                batch = self.db.get(ImportBatch, row.import_batch_id)
                if batch and (batch.is_synthetic or is_test_source(batch.data_source) or is_synthetic_source(batch.data_source)):
                    continue
            eligible.append(row)
        return eligible

    def _paired_rows(self, req: BacktestRequest):
        a, b = req.pair.split("-")
        rows_a = self._eligible_rows(a, req.start_date, req.end_date)
        rows_b = self._eligible_rows(b, req.start_date, req.end_date)
        map_b = {(row.trade_date, row.expiry_date): row for row in rows_b}

        # Match exact expiries, then keep only the nearest shared expiry per
        # trading session. This mirrors the analytics series and prevents a
        # multi-expiry session from being counted as several independent days.
        pairs_by_date = {}
        for row_a in sorted(rows_a, key=lambda row: (row.trade_date, row.expiry_date)):
            key = (row_a.trade_date, row_a.expiry_date)
            row_b = map_b.get(key)
            if row_b is not None:
                pairs_by_date.setdefault(row_a.trade_date, (row_a, row_b))

        pairs = [pairs_by_date[day] for day in sorted(pairs_by_date)]
        return [(oa, ob, round(oa.normalized_price_10g_basis - ob.normalized_price_10g_basis, 6)) for oa, ob in pairs]

    @staticmethod
    def _has_sufficient_observed_volume(oa: MarketObservation, ob: MarketObservation, min_volume: int) -> bool:
        """Require both legs to have explicitly observed, valid volume values."""
        volumes = []
        for row in (oa, ob):
            volume = row.volume
            if (
                not row.volume_observed
                or isinstance(volume, bool)
                or not isinstance(volume, (int, float))
                or not isfinite(volume)
                or volume < 0
            ):
                return False
            volumes.append(volume)
        return min(volumes) >= min_volume

    @staticmethod
    def _empty(req: BacktestRequest, status: str, message: str, count: int = 0, first=None, last=None):
        return BacktestResponse(
            status=status, message=message, pair=req.pair, observations=count,
            first_date=first, last_date=last, metrics=BacktestMetricSet(), assumptions=ASSUMPTIONS,
        )

    def run(self, req: BacktestRequest) -> BacktestResponse:
        pairs = self._paired_rows(req)
        if not pairs:
            return self._empty(
                req, "no_eligible_data",
                "No eligible non-synthetic, non-test history is available for this pair. Upload a user-provided historical CSV to run a backtest; uploaded data is not provider-verified.",
            )
        first_date, last_date = pairs[0][0].trade_date, pairs[-1][0].trade_date
        if len(pairs) < req.lookback + 2:
            return self._empty(
                req, "insufficient_history",
                f"This pair has {len(pairs)} synchronized eligible observations; at least {req.lookback + 2} are needed for the selected lookback.",
                len(pairs), first_date, last_date,
            )

        spreads = [point[2] for point in pairs]
        z_scores: List[Optional[float]] = [None] * len(spreads)
        for idx in range(req.lookback - 1, len(spreads)):
            window = spreads[idx - req.lookback + 1 : idx + 1]
            sigma = stdev(window) if len(window) > 1 else 0.0
            if sigma > 0 and isfinite(sigma):
                z_scores[idx] = (spreads[idx] - mean(window)) / sigma

        capital = req.capital
        equity = capital
        peak = capital
        max_drawdown = 0.0
        points = [EquityPoint(trade_date=pairs[0][0].trade_date, equity=round(capital, 2), drawdown_pct=0.0)]
        returns: List[float] = []
        trades: List[BacktestTrade] = []
        open_trade: Optional[Dict] = None
        gross_total = 0.0
        total_costs = 0.0
        half_cost = (req.transaction_cost_per_10g + req.slippage_per_10g) * req.units / 2

        for idx in range(1, len(pairs)):
            oa, ob, spread = pairs[idx]
            previous_spread = spreads[idx - 1]
            daily_pnl = 0.0
            if open_trade:
                daily_pnl = (spread - previous_spread) * open_trade["sign"] * req.units
                equity += daily_pnl
                gross_total += daily_pnl

            z = z_scores[idx - 1]
            if open_trade and (z is not None and abs(z) <= req.exit_z):
                equity -= half_cost
                total_costs += half_cost
                gross_trade = open_trade["gross_pnl"] + daily_pnl
                net_trade = gross_trade - half_cost * 2
                trades.append(self._trade(open_trade, oa, ob, spread, req.units, gross_trade, half_cost * 2, net_trade, "Z-score reverted"))
                open_trade = None
            elif not open_trade and z is not None and abs(z) >= req.entry_z:
                dte_a = (oa.expiry_date - oa.trade_date).days
                dte_b = (ob.expiry_date - ob.trade_date).days
                liquid = self._has_sufficient_observed_volume(oa, ob, req.min_volume)
                expiry_clear = min(dte_a, dte_b) > req.expiry_buffer_days
                if liquid and expiry_clear:
                    sign = -1 if z > 0 else 1
                    equity -= half_cost
                    total_costs += half_cost
                    open_trade = {
                        "entry_date": oa.trade_date, "entry_spread": spread, "sign": sign,
                        "gross_pnl": 0.0, "direction": "Short spread" if sign < 0 else "Long spread",
                    }
            if open_trade:
                open_trade["gross_pnl"] += daily_pnl

            peak = max(peak, equity)
            drawdown = ((equity - peak) / peak * 100) if peak else 0.0
            max_drawdown = min(max_drawdown, drawdown)
            previous_equity = points[-1].equity
            if previous_equity:
                returns.append((equity - previous_equity) / previous_equity)
            points.append(EquityPoint(trade_date=oa.trade_date, equity=round(equity, 2), drawdown_pct=round(drawdown, 4)))

        if open_trade:
            oa, ob, spread = pairs[-1]
            equity -= half_cost
            total_costs += half_cost
            gross_trade = open_trade["gross_pnl"]
            trades.append(self._trade(open_trade, oa, ob, spread, req.units, gross_trade, half_cost * 2, gross_trade - half_cost * 2, "End of history"))
            peak = max(peak, equity)
            drawdown = ((equity - peak) / peak * 100) if peak else 0.0
            max_drawdown = min(max_drawdown, drawdown)
            points[-1] = EquityPoint(trade_date=oa.trade_date, equity=round(equity, 2), drawdown_pct=round(drawdown, 4))

        closed_wins = sum(1 for trade in trades if trade.net_pnl > 0)
        losses = sum(-trade.net_pnl for trade in trades if trade.net_pnl < 0)
        wins = sum(trade.net_pnl for trade in trades if trade.net_pnl > 0)
        volatility = stdev(returns) if len(returns) > 1 else 0
        sharpe = (mean(returns) / volatility * sqrt(252)) if volatility > 0 else None
        metrics = BacktestMetricSet(
            total_return_pct=round((equity - capital) / capital * 100, 4),
            total_pnl=round(equity - capital, 2), max_drawdown_pct=round(max_drawdown, 4),
            sharpe_ratio=round(sharpe, 4) if sharpe is not None and isfinite(sharpe) else None,
            win_rate_pct=round(closed_wins / len(trades) * 100, 2) if trades else None,
            total_trades=len(trades), profit_factor=round(wins / losses, 4) if losses > 0 else None,
            gross_pnl=round(gross_total, 2), total_costs=round(total_costs, 2),
        )
        markers = {}
        for trade in trades:
            markers[trade.entry_date] = "Entry · " + ("long" if trade.direction == "Long spread" else "short")
            markers[trade.exit_date] = "Exit"
        spread_series = [
            SpreadPoint(trade_date=oa.trade_date, spread=spread, execution=markers.get(oa.trade_date))
            for oa, _ob, spread in pairs
        ]
        return BacktestResponse(
            status="completed", message="Historical walk-forward simulation completed.", pair=req.pair,
            data_source="User-imported historical observations (not provider-verified)", first_date=first_date, last_date=last_date,
            observations=len(pairs), metrics=metrics, equity_curve=points, spread_series=spread_series,
            trades=trades, assumptions=ASSUMPTIONS,
        )

    @staticmethod
    def _trade(open_trade, oa, ob, exit_spread, units, gross, costs, net, reason):
        return BacktestTrade(
            entry_date=open_trade["entry_date"], exit_date=oa.trade_date, pair=f"{oa.symbol}-{ob.symbol}",
            direction=open_trade["direction"], entry_spread=round(open_trade["entry_spread"], 4),
            exit_spread=round(exit_spread, 4), units=units, gross_pnl=round(gross, 2), costs=round(costs, 2),
            net_pnl=round(net, 2), exit_reason=reason,
        )
