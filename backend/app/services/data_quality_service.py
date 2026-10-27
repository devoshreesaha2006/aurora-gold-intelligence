"""Read-only coverage and synchronized-expiry audit for stored observations."""
from collections import Counter, defaultdict

from backend.app.models.contract import Contract
from backend.app.models.market_observation import MarketObservation
from backend.app.services.data_provenance import eligible_analytics_observations_query


class DataQualityService:
    def __init__(self, db):
        self.db = db

    def report(self):
        stored = self.db.query(MarketObservation).order_by(
            MarketObservation.trade_date, MarketObservation.expiry_date
        ).all()
        eligible_ids = {row.id for row in eligible_analytics_observations_query(self.db).all()}
        symbols = sorted({row.symbol for row in stored} | {item.symbol for item in self.db.query(Contract).all()})
        by_symbol = {}
        eligible_rows = []
        for symbol in symbols:
            rows = [row for row in stored if row.symbol == symbol]
            eligible = [row for row in rows if row.id in eligible_ids]
            eligible_rows.extend(eligible)
            by_symbol[symbol] = {
                "stored_observations": len(rows),
                "eligible_observations": len(eligible),
                "first_trade_date": min((r.trade_date for r in rows), default=None),
                "last_trade_date": max((r.trade_date for r in rows), default=None),
                "eligible_first_trade_date": min((r.trade_date for r in eligible), default=None),
                "eligible_last_trade_date": max((r.trade_date for r in eligible), default=None),
                "missing_volume_observation_count": sum(not r.volume_observed for r in rows),
                "observed_zero_volume_count": sum(r.volume_observed and r.volume == 0 for r in rows),
                "missing_open_interest_observation_count": sum(not r.open_interest_observed for r in rows),
                "observed_zero_open_interest_count": sum(r.open_interest_observed and r.open_interest == 0 for r in rows),
                "provider_verified_observation_count": sum(r.is_provider_verified for r in rows),
            }

        # Count exact synchronized sessions only. Different expiries are not
        # considered a match, and each contract pair/date is counted once.
        keys_by_symbol = defaultdict(set)
        for row in eligible_rows:
            keys_by_symbol[row.symbol].add((row.trade_date, row.expiry_date))
        pair_counts = {}
        for i, a in enumerate(symbols):
            for b in symbols[i + 1:]:
                pair_counts[f"{a}-{b}"] = len(keys_by_symbol[a] & keys_by_symbol[b])

        source_counts = Counter()
        for row in stored:
            # Keep raw provenance labels distinct; this is not a source-authenticity verdict.
            source_counts[row.data_source or "unlabelled"] += 1
        return {
            "status": "available" if stored else "empty",
            "stored_observation_count": len(stored),
            "eligible_observation_count": len(eligible_rows),
            "excluded_by_eligibility_count": len(stored) - len(eligible_rows),
            "provider_verified_observation_count": sum(r.is_provider_verified for r in stored),
            "bid_ask_observation_count": 0,
            "data_source_counts": dict(sorted(source_counts.items())),
            "symbols": by_symbol,
            "exact_trade_date_and_expiry_pair_counts": pair_counts,
            "method": "Coverage counts use existing analytics provenance eligibility and explicit (trade_date, expiry_date) keys. Zero is counted as observed only when its observation flag is true.",
            "provenance_limit": "Stored source labels do not independently authenticate an exchange source; CSV remains user-imported/unverified unless a verified provider observation is recorded.",
            "limitations": [
                "No bid/ask history is stored; executable spread and per-leg fill quality cannot be validated.",
                "Tender-period dates are not stored in the contract or observation schema.",
                "Contract quote-unit and purity specifications are current configuration, not effective-dated historical records.",
            ],
        }
