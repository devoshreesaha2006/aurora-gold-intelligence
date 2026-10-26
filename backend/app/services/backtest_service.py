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
    "P&L is only booked between consecutive sessions of the same expiry pair. If the nearest shared expiry changes while a position is open, the position is closed at the last settlement of the expiring pair (exit costs charged once); the level difference between the two contract pairs is never booked as P&L.",
    "Passive benchmark returns use first-to-last normalized settlement price changes for each leg, scaled to starting capital; they are transparent reference comparisons, not exposure-matched alpha or executable investment returns.",
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

    def _no_pair_data_message(self, req: BacktestRequest) -> str:
        leg_a, leg_b = req.pair.split("-")
        rows_a = self._eligible_rows(leg_a, req.start_date, req.end_date)
        rows_b = self._eligible_rows(leg_b, req.start_date, req.end_date)
        if req.start_date or req.end_date:
            window = f"the selected date window ({req.start_date or 'start of history'} through {req.end_date or 'latest'})"
        else:
            window = "stored history"

        if rows_a and rows_b:
            return (
                f"No synchronized {leg_a}-{leg_b} observations are available in {window}. "
                "Both legs have eligible history, but no rows share the same trade date and explicit expiry. "
                "Different expiries are never paired. Expand or change the date window, or choose another pair."
            )
        missing = [symbol for symbol, rows in ((leg_a, rows_a), (leg_b, rows_b)) if not rows]
        if len(missing) == 1:
            return (
                f"No eligible {missing[0]} observations are available in {window}; both pair legs need "
                "eligible non-test, non-synthetic history. Change the date window or pair; import history "
                "only if the required records are not already stored."
            )
        return (
            f"No eligible observations for either {leg_a} or {leg_b} are available in {window}. "
            "Test and synthetic rows are excluded. Change the date window or pair, or import user-provided "
            "historical records if the required data is not already stored."
        )

    def run(self, req: BacktestRequest) -> BacktestResponse:
        pairs = self._paired_rows(req)
        if not pairs:
            return self._empty(
                req, "no_eligible_data",
                self._no_pair_data_message(req),
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
        entry_setups = 0
        volume_blocked_entries = 0
        expiry_blocked_entries = 0
        half_cost = (req.transaction_cost_per_10g + req.slippage_per_10g) * req.units / 2

        for idx in range(1, len(pairs)):
            oa, ob, spread = pairs[idx]
            previous_spread = spreads[idx - 1]
            daily_pnl = 0.0
            if open_trade and oa.expiry_date != pairs[idx - 1][0].expiry_date:
                # A new contract pair has a different level; do not book that jump as P&L.
                prev_oa, prev_ob, prev_spread = pairs[idx - 1]
                equity -= half_cost
                total_costs += half_cost
                gross_trade = open_trade["gross_pnl"]
                trades.append(self._trade(
                    open_trade, prev_oa, prev_ob, prev_spread, req.units, gross_trade, half_cost * 2,
                    gross_trade - half_cost * 2, "Expiry roll (pair changed)",
                ))
                open_trade = None
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
                entry_setups += 1
                dte_a = (oa.expiry_date - oa.trade_date).days
                dte_b = (ob.expiry_date - ob.trade_date).days
                liquid = self._has_sufficient_observed_volume(oa, ob, req.min_volume)
                expiry_clear = min(dte_a, dte_b) > req.expiry_buffer_days
                if not liquid:
                    volume_blocked_entries += 1
                if not expiry_clear:
                    expiry_blocked_entries += 1
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
                returns.append((round(equity, 2) - previous_equity) / previous_equity)
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
            # Include the final exit cost in the last daily return so the
            # annualized Sharpe ratio reflects the same terminal equity as P&L.
            if len(points) > 1 and points[-2].equity:
                final_return = (round(equity, 2) - points[-2].equity) / points[-2].equity
                if returns:
                    returns[-1] = final_return

        closed_wins = sum(1 for trade in trades if trade.net_pnl > 0)
        losses = sum(-trade.net_pnl for trade in trades if trade.net_pnl < 0)
        wins = sum(trade.net_pnl for trade in trades if trade.net_pnl > 0)
        volatility = stdev(returns) if len(returns) > 1 else 0
        sharpe = (mean(returns) / volatility * sqrt(252)) if volatility > 0 else None
        # Attribute the strategy result against each outright leg's normalized gold-price
        # movement over the identical observed window. These capital-scaled passive
        # benchmarks are explicitly not exposure/risk-matched to a spread strategy.
        first_a, first_b, _ = pairs[0]
        last_a, last_b, _ = pairs[-1]
        benchmark_a_return = ((last_a.normalized_price_10g_basis / first_a.normalized_price_10g_basis) - 1) * 100 if first_a.normalized_price_10g_basis else None
        benchmark_b_return = ((last_b.normalized_price_10g_basis / first_b.normalized_price_10g_basis) - 1) * 100 if first_b.normalized_price_10g_basis else None
        benchmark_a_pnl = capital * benchmark_a_return / 100 if benchmark_a_return is not None else None
        benchmark_b_pnl = capital * benchmark_b_return / 100 if benchmark_b_return is not None else None
        strategy_return = ((equity - capital) / capital) * 100 if capital else None
        metrics = BacktestMetricSet(
            total_return_pct=round((equity - capital) / capital * 100, 4),
            total_pnl=round(equity - capital, 2), max_drawdown_pct=round(max_drawdown, 4),
            sharpe_ratio=round(sharpe, 4) if sharpe is not None and isfinite(sharpe) else None,
            win_rate_pct=round(closed_wins / len(trades) * 100, 2) if trades else None,
            total_trades=len(trades), profit_factor=round(wins / losses, 4) if losses > 0 else None,
            gross_pnl=round(gross_total, 2), total_costs=round(total_costs, 2),
            benchmark_leg_a_return_pct=round(benchmark_a_return, 4) if benchmark_a_return is not None else None,
            benchmark_leg_b_return_pct=round(benchmark_b_return, 4) if benchmark_b_return is not None else None,
            benchmark_leg_a_pnl=round(benchmark_a_pnl, 2) if benchmark_a_pnl is not None else None,
            benchmark_leg_b_pnl=round(benchmark_b_pnl, 2) if benchmark_b_pnl is not None else None,
            excess_return_vs_leg_a_pct=round(strategy_return - benchmark_a_return, 4) if strategy_return is not None and benchmark_a_return is not None else None,
            excess_return_vs_leg_b_pct=round(strategy_return - benchmark_b_return, 4) if strategy_return is not None and benchmark_b_return is not None else None,
        )
        markers = {}
        for trade in trades:
            markers[trade.entry_date] = "Entry · " + ("long" if trade.direction == "Long spread" else "short")
            markers[trade.exit_date] = "Exit"
        spread_series = [
            SpreadPoint(trade_date=oa.trade_date, spread=spread, execution=markers.get(oa.trade_date))
            for oa, _ob, spread in pairs
        ]
        message = (
            f"Historical walk-forward simulation completed with {len(trades)} completed trade(s) "
            f"across {len(pairs)} synchronized observations. "
            f"{entry_setups} entry-threshold check(s); {volume_blocked_entries} blocked by observed-volume "
            f"requirements and {expiry_blocked_entries} blocked by the expiry buffer."
        )
        if not trades:
            if entry_setups == 0:
                message = (
                    f"Historical simulation completed with no trades across {len(pairs)} synchronized "
                    "observations: no eligible observation crossed the configured entry threshold. "
                    "Compare another preset or pair; do not lower thresholds solely to force trades."
                )
            else:
                skipped = []
                if volume_blocked_entries:
                    skipped.append(f"{volume_blocked_entries} entry check(s) failed the observed-volume requirement")
                if expiry_blocked_entries:
                    skipped.append(f"{expiry_blocked_entries} entry check(s) fell inside the {req.expiry_buffer_days}-day expiry buffer")
                message = (
                    f"Historical simulation completed with no trades from {entry_setups} entry-threshold check(s): "
                    + ("; ".join(skipped) if skipped else "all candidate entries were unavailable")
                    + "."
                )
        return BacktestResponse(
            status="completed", message=message, pair=req.pair,
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
