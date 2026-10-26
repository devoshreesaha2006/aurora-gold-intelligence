"""Expiry-aware term-structure diagnostics for normalized MCX gold spreads.

Curve-level changes are reported separately from changes caused by switching the
front shared expiry. Neither settlement series is an executable quote.
"""
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from backend.app.models.market_observation import MarketObservation
from backend.app.services.analytics_service import parse_pair
from backend.app.services.data_provenance import eligible_analytics_observations_query


class TermStructureService:
    def __init__(self, db: Session):
        self.db = db

    def report(self, pair: str, start_date: Optional[date] = None, end_date: Optional[date] = None):
        leg_a, leg_b, inverted = parse_pair(pair)
        qa = eligible_analytics_observations_query(self.db).filter(MarketObservation.symbol == leg_a)
        qb = eligible_analytics_observations_query(self.db).filter(MarketObservation.symbol == leg_b)
        if start_date:
            qa = qa.filter(MarketObservation.trade_date >= start_date)
            qb = qb.filter(MarketObservation.trade_date >= start_date)
        if end_date:
            qa = qa.filter(MarketObservation.trade_date <= end_date)
            qb = qb.filter(MarketObservation.trade_date <= end_date)
        rows_a = qa.order_by(MarketObservation.trade_date, MarketObservation.expiry_date).all()
        rows_b = qb.order_by(MarketObservation.trade_date, MarketObservation.expiry_date).all()
        b_by_key = {(r.trade_date, r.expiry_date): r for r in rows_b}

        by_day = {}
        for a in rows_a:
            b = b_by_key.get((a.trade_date, a.expiry_date))
            if b is None:
                continue
            spread = a.normalized_price_10g_basis - b.normalized_price_10g_basis
            if inverted:
                spread = -spread
            by_day.setdefault(a.trade_date, []).append({
                "trade_date": a.trade_date.isoformat(),
                "expiry_date": a.expiry_date.isoformat(),
                "days_to_expiry": (a.expiry_date - a.trade_date).days,
                "spread": round(spread, 6),
                "price_a": round(b.normalized_price_10g_basis if inverted else a.normalized_price_10g_basis, 6),
                "price_b": round(a.normalized_price_10g_basis if inverted else b.normalized_price_10g_basis, 6),
                "volume_a": a.volume if a.volume_observed else None,
                "volume_b": b.volume if b.volume_observed else None,
                "open_interest_a": a.open_interest if a.open_interest_observed else None,
                "open_interest_b": b.open_interest if b.open_interest_observed else None,
            })

        curve = []
        front = []
        previous_spread_by_expiry = {}
        previous_front = None
        for day in sorted(by_day):
            points = sorted(by_day[day], key=lambda p: p["expiry_date"])
            current_expiry_spreads = {}
            for point in points:
                prior = previous_spread_by_expiry.get(point["expiry_date"])
                point["same_expiry_spread_change"] = round(point["spread"] - prior, 6) if prior is not None else None
                current_expiry_spreads[point["expiry_date"]] = point["spread"]
            chosen = points[0]
            prior_front = previous_front
            chosen["front_same_expiry_change"] = (
                chosen["same_expiry_spread_change"]
                if prior_front is not None and prior_front["expiry_date"] == chosen["expiry_date"]
                else None
            )
            # A pure same-session switch gap is measurable only when both the
            # previous front expiry and the new front expiry are observed today.
            # Never subtract yesterday's settlement: that would mix market move
            # and contract-switch effects.
            prior_front_today = next(
                (point for point in points if prior_front is not None and point["expiry_date"] == prior_front["expiry_date"]),
                None,
            )
            chosen["front_switch_gap"] = (
                round(chosen["spread"] - prior_front_today["spread"], 6)
                if prior_front is not None
                and prior_front["expiry_date"] != chosen["expiry_date"]
                and prior_front_today is not None
                else None
            )
            chosen["front_switch_gap_available"] = chosen["front_switch_gap"] is not None
            chosen["front_expiry_changed"] = bool(
                prior_front is not None and prior_front["expiry_date"] != chosen["expiry_date"]
            )
            front.append(dict(chosen))
            curve.append({"trade_date": day.isoformat(), "contracts": points})
            previous_front = chosen
            previous_spread_by_expiry = current_expiry_spreads

        roll_gaps = [p["front_switch_gap"] for p in front if p["front_switch_gap"] is not None]
        same_expiry_moves = [p["front_same_expiry_change"] for p in front if p["front_same_expiry_change"] is not None]
        return {
            "pair": f"{leg_b}-{leg_a}" if inverted else f"{leg_a}-{leg_b}",
            "status": "available" if curve else "no_eligible_data",
            "observations": len(front),
            "curve_snapshots": curve,
            "front_series": front,
            "decomposition": {
                "same_expiry_front_change_count": len(same_expiry_moves),
                "front_expiry_switch_count": len(roll_gaps),
                "cumulative_same_expiry_front_change": round(sum(same_expiry_moves), 6),
                "cumulative_front_switch_gaps": round(sum(roll_gaps), 6),
                "note": "Front-switch gaps are reported separately and are not strategy P&L. Same-expiry changes compare the same explicit expiry across adjacent observed dates; gaps in dates are not forward-filled.",
            },
            "data_quality": {
                "source_note": "Eligible stored observations only; imported CSV is not provider-verified unless the market status explicitly confirms an authorized provider.",
                "execution_note": "Normalized settlement/close values are analytical references, not executable bid/ask quotes.",
                "synchronized_by": "exact trade date and explicit expiry",
            },
        }
