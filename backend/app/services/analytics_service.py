import math
from datetime import date, datetime
from typing import List, Dict, Tuple, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import numpy as np

from backend.app.models.market_observation import MarketObservation
from backend.app.models.contract import Contract
from backend.app.services.data_provenance import eligible_analytics_observations_query
from backend.app.schemas.analytics import (
    PairSpreadPoint, PairSpreadResponse, CostHurdleAssumptions,
    PairRadarItem, RadarResponse, RelativeValueEvent, EventsResponse,
    EventEvidenceTrail, DistributionResponse
)

# Canonical 6 Pair Combinations in MCX Gold
VALID_PAIRS: List[Tuple[str, str]] = [
    ("GOLDM", "GOLDTEN"),
    ("GOLDM", "GOLDGUINEA"),
    ("GOLDM", "GOLDPETAL"),
    ("GOLDTEN", "GOLDGUINEA"),
    ("GOLDTEN", "GOLDPETAL"),
    ("GOLDGUINEA", "GOLDPETAL"),
]

VALID_PAIR_STRINGS = [f"{a}-{b}" for a, b in VALID_PAIRS]


def parse_pair(pair_str: str) -> Tuple[str, str, bool]:
    """
    Parses a pair string like 'GOLDM-GOLDPETAL' or 'GOLDPETAL-GOLDM'.
    Returns (leg_a, leg_b, is_inverted).
    """
    clean = pair_str.strip().upper().replace("/", "-").replace("_", "-")
    parts = clean.split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid pair format '{pair_str}'. Expected format: 'CONTRACT_A-CONTRACT_B'.")
    
    a, b = parts[0].strip(), parts[1].strip()
    
    # Check canonical direction
    if (a, b) in VALID_PAIRS:
        return a, b, False
    elif (b, a) in VALID_PAIRS:
        # Inverted pair
        return b, a, True
    else:
        raise ValueError(f"Unsupported pair '{pair_str}'. Supported contracts: GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL.")


def calculate_cost_hurdle(
    ref_price: float = 62500.0,
    stt_rate_pct: float = 0.01,
    exchange_fee_pct: float = 0.0025,
    brokerage_per_10g: float = 2.50,
    slippage_buffer_per_10g: float = 15.00
) -> CostHurdleAssumptions:
    """
    Computes institutional trading friction hurdle in ₹ per 10g benchmark basis:
    - STT on turnover (sell side): 0.01%
    - MCX Transaction + SEBI regulatory charge: ~0.0025%
    - Brokerage hurdle: ~₹2.50 per 10g
    - Slippage & market impact buffer: ~₹15.00 per 10g
    """
    turnover_10g = ref_price
    stt_cost = turnover_10g * (stt_rate_pct / 100.0)
    exchange_cost = turnover_10g * (exchange_fee_pct / 100.0)
    total_hurdle = round(stt_cost + exchange_cost + brokerage_per_10g + slippage_buffer_per_10g, 2)

    return CostHurdleAssumptions(
        stt_rate_pct=stt_rate_pct,
        exchange_fee_pct=exchange_fee_pct,
        brokerage_per_10g=brokerage_per_10g,
        slippage_buffer_per_10g=slippage_buffer_per_10g,
        total_roundtrip_cost_per_10g=total_hurdle
    )


class RelativeValueAnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_synchronized_observations(
        self,
        leg_a: str,
        leg_b: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Tuple[MarketObservation, MarketObservation]]:
        """
        Retrieves synchronized observations where both legs match on trade_date AND
        expiry_date. Avoids pairing different contract expiries, forward-filling, or
        fabricated quotes.
        """
        # Fetch Leg A observations
        query_a = eligible_analytics_observations_query(self.db).filter(MarketObservation.symbol == leg_a)
        if start_date:
            query_a = query_a.filter(MarketObservation.trade_date >= start_date)
        if end_date:
            query_a = query_a.filter(MarketObservation.trade_date <= end_date)
        obs_a = query_a.order_by(MarketObservation.trade_date.asc(), MarketObservation.expiry_date.asc()).all()

        # Fetch Leg B observations
        query_b = eligible_analytics_observations_query(self.db).filter(MarketObservation.symbol == leg_b)
        if start_date:
            query_b = query_b.filter(MarketObservation.trade_date >= start_date)
        if end_date:
            query_b = query_b.filter(MarketObservation.trade_date <= end_date)
        obs_b = query_b.order_by(MarketObservation.trade_date.asc(), MarketObservation.expiry_date.asc()).all()

        # An instrument can have multiple listed expiries on one trade date. Pair only
        # the same dated contract; a date-only map silently crossed those contracts.
        map_b = {(b.trade_date, b.expiry_date): b for b in obs_b}
        synchronized_by_date: Dict[date, Tuple[MarketObservation, MarketObservation]] = {}
        for a in obs_a:
            key = (a.trade_date, a.expiry_date)
            if key in map_b:
                # When more than one common expiry is present, use the nearest
                # available common expiry (front contract) once per session.
                synchronized_by_date.setdefault(a.trade_date, (a, map_b[key]))

        return [synchronized_by_date[trade_day] for trade_day in sorted(synchronized_by_date)]

    def calculate_pairwise_spread_series(
        self,
        leg_a: str,
        leg_b: str,
        window_days: int = 30,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        invert_spread: bool = False
    ) -> PairSpreadResponse:
        """
        Calculates normalized spread series between two contracts:
        Spread(t) = NormPrice_A(t) - NormPrice_B(t) (in ₹ per 10g benchmark 995 basis)
        Calculates trailing rolling mean, unbiased sample standard deviation (ddof=1),
        rolling Z-score, and empirical percentile rank with zero future look-ahead.
        """
        pairs = self.get_synchronized_observations(leg_a, leg_b, start_date, end_date)
        pair_name = f"{leg_a}-{leg_b}" if not invert_spread else f"{leg_b}-{leg_a}"

        if not pairs:
            return PairSpreadResponse(
                pair=pair_name,
                leg_a=leg_a if not invert_spread else leg_b,
                leg_b=leg_b if not invert_spread else leg_a,
                window_days=window_days,
                total_points=0,
                data_points=[]
            )

        data_points: List[PairSpreadPoint] = []
        spread_history: List[float] = []

        for i, (oa, ob) in enumerate(pairs):
            spread_val = oa.normalized_price_10g_basis - ob.normalized_price_10g_basis
            if invert_spread:
                spread_val = -spread_val

            spread_history.append(spread_val)

            # Trailing lookback window strictly up to index i (zero look-ahead)
            start_idx = max(0, i - window_days + 1)
            window_slice = spread_history[start_idx : i + 1]
            n_obs = len(window_slice)

            # Days to expiry
            dte_a = (oa.expiry_date - oa.trade_date).days if oa.expiry_date and oa.trade_date else None
            dte_b = (ob.expiry_date - ob.trade_date).days if ob.expiry_date and ob.trade_date else None

            # Statistical calculations
            if n_obs < 2:
                # Insufficient history for sample variance
                data_points.append(PairSpreadPoint(
                    trade_date=oa.trade_date,
                    expiry_date=oa.expiry_date,
                    spread=round(spread_val, 2),
                    price_a=oa.normalized_price_10g_basis if not invert_spread else ob.normalized_price_10g_basis,
                    price_b=ob.normalized_price_10g_basis if not invert_spread else oa.normalized_price_10g_basis,
                    raw_price_a=oa.close_price if not invert_spread else ob.close_price,
                    raw_price_b=ob.close_price if not invert_spread else oa.close_price,
                    rolling_mean=round(float(np.mean(window_slice)), 2),
                    rolling_std=None,
                    z_score=None,
                    percentile_rank=None,
                    upper_2sigma=None,
                    lower_2sigma=None,
                    upper_1sigma=None,
                    lower_1sigma=None,
                    volume_a=(oa.volume if oa.volume_observed else None) if not invert_spread else (ob.volume if ob.volume_observed else None),
                    volume_b=(ob.volume if ob.volume_observed else None) if not invert_spread else (oa.volume if oa.volume_observed else None),
                    open_interest_a=(oa.open_interest if oa.open_interest_observed else None) if not invert_spread else (ob.open_interest if ob.open_interest_observed else None),
                    open_interest_b=(ob.open_interest if ob.open_interest_observed else None) if not invert_spread else (oa.open_interest if oa.open_interest_observed else None),
                    dte_a=dte_a if not invert_spread else dte_b,
                    dte_b=dte_b if not invert_spread else dte_a,
                    status="insufficient_history"
                ))
            else:
                mean_val = float(np.mean(window_slice))
                std_val = float(np.std(window_slice, ddof=1)) # Unbiased sample standard deviation

                if std_val < 1e-6:
                    # Zero variance in window
                    data_points.append(PairSpreadPoint(
                        trade_date=oa.trade_date,
                        expiry_date=oa.expiry_date,
                        spread=round(spread_val, 2),
                        price_a=oa.normalized_price_10g_basis if not invert_spread else ob.normalized_price_10g_basis,
                        price_b=ob.normalized_price_10g_basis if not invert_spread else oa.normalized_price_10g_basis,
                        raw_price_a=oa.close_price if not invert_spread else ob.close_price,
                        raw_price_b=ob.close_price if not invert_spread else oa.close_price,
                        rolling_mean=round(mean_val, 2),
                        rolling_std=0.0,
                        z_score=None,
                        percentile_rank=50.0,
                        upper_2sigma=round(mean_val, 2),
                        lower_2sigma=round(mean_val, 2),
                        upper_1sigma=round(mean_val, 2),
                        lower_1sigma=round(mean_val, 2),
                        volume_a=(oa.volume if oa.volume_observed else None) if not invert_spread else (ob.volume if ob.volume_observed else None),
                        volume_b=(ob.volume if ob.volume_observed else None) if not invert_spread else (oa.volume if oa.volume_observed else None),
                        open_interest_a=(oa.open_interest if oa.open_interest_observed else None) if not invert_spread else (ob.open_interest if ob.open_interest_observed else None),
                        open_interest_b=(ob.open_interest if ob.open_interest_observed else None) if not invert_spread else (oa.open_interest if oa.open_interest_observed else None),
                        dte_a=dte_a if not invert_spread else dte_b,
                        dte_b=dte_b if not invert_spread else dte_a,
                        status="zero_variance"
                    ))
                else:
                    z_val = (spread_val - mean_val) / std_val

                    # Empirical percentile rank within window slice
                    less_count = sum(1 for x in window_slice if x < spread_val)
                    equal_count = sum(1 for x in window_slice if x == spread_val)
                    percentile_val = ((less_count + 0.5 * equal_count) / n_obs) * 100.0

                    data_points.append(PairSpreadPoint(
                        trade_date=oa.trade_date,
                        expiry_date=oa.expiry_date,
                        spread=round(spread_val, 2),
                        price_a=oa.normalized_price_10g_basis if not invert_spread else ob.normalized_price_10g_basis,
                        price_b=ob.normalized_price_10g_basis if not invert_spread else oa.normalized_price_10g_basis,
                        raw_price_a=oa.close_price if not invert_spread else ob.close_price,
                        raw_price_b=ob.close_price if not invert_spread else oa.close_price,
                        rolling_mean=round(mean_val, 2),
                        rolling_std=round(std_val, 2),
                        z_score=round(z_val, 2),
                        percentile_rank=round(percentile_val, 1),
                        upper_2sigma=round(mean_val + 2 * std_val, 2),
                        lower_2sigma=round(mean_val - 2 * std_val, 2),
                        upper_1sigma=round(mean_val + std_val, 2),
                        lower_1sigma=round(mean_val - std_val, 2),
                        volume_a=(oa.volume if oa.volume_observed else None) if not invert_spread else (ob.volume if ob.volume_observed else None),
                        volume_b=(ob.volume if ob.volume_observed else None) if not invert_spread else (oa.volume if oa.volume_observed else None),
                        open_interest_a=(oa.open_interest if oa.open_interest_observed else None) if not invert_spread else (ob.open_interest if ob.open_interest_observed else None),
                        open_interest_b=(ob.open_interest if ob.open_interest_observed else None) if not invert_spread else (oa.open_interest if oa.open_interest_observed else None),
                        dte_a=dte_a if not invert_spread else dte_b,
                        dte_b=dte_b if not invert_spread else dte_a,
                        status="valid"
                    ))

        return PairSpreadResponse(
            pair=pair_name,
            leg_a=leg_a if not invert_spread else leg_b,
            leg_b=leg_b if not invert_spread else leg_a,
            window_days=window_days,
            total_points=len(data_points),
            data_points=data_points
        )

    def classify_relative_value_state(
        self,
        spread: Optional[float],
        rolling_mean: Optional[float],
        z_score: Optional[float],
        percentile: Optional[float],
        dte_min: Optional[int],
        min_volume: Optional[int],
        min_open_interest: Optional[int],
        cost_hurdle: float = 25.0,
        z_investigate_threshold: float = 1.5,
        z_watch_threshold: float = 1.0,
        expiry_risk_days: int = 5,
        min_liquidity_volume: int = 100,
        min_liquidity_oi: int = 500
    ) -> Tuple[str, Optional[float], Optional[float], bool, bool, bool, Optional[float], Optional[float], str]:
        """
        Applies transparent decision logic to classify the state into:
        - Expiry-Risk: Contract in roll window / tender delivery period (DTE <= 5 days).
        - Cost-Blocked: Apparent gross dislocation is smaller than transaction friction.
        - Watch: Moderate statistical dislocation, thin liquidity, or short history.
        - Investigate: Statistically significant dislocation (|Z| >= threshold) with positive net edge.
        - No Signal: Spread is within normal statistical equilibrium.
        
        Returns:
        (classification, opportunity_score, trap_risk_score, is_expiry_risk, is_cost_blocked, is_liquidity_trap, gross_edge, net_edge, reason)
        """
        if spread is None or rolling_mean is None or z_score is None:
            return (
                "No Signal",
                None,
                None,
                False,
                False,
                False,
                None,
                None,
                "Insufficient synchronized history to calculate a statistical baseline."
            )

        gross_edge = round(abs(spread - rolling_mean), 2)
        net_edge = round(gross_edge - cost_hurdle, 2)

        is_expiry_risk = (dte_min is not None and dte_min <= expiry_risk_days)
        is_cost_blocked = (gross_edge <= cost_hurdle)
        liquidity_known = min_volume is not None and min_open_interest is not None
        is_liquidity_trap = liquidity_known and (
            min_volume < min_liquidity_volume or min_open_interest < min_liquidity_oi
        )

        # Trap Risk Score (0-100)
        trap_score = 0.0
        if is_expiry_risk:
            trap_score += 45.0
        elif dte_min is not None and dte_min <= 10:
            trap_score += 20.0

        if is_cost_blocked:
            trap_score += 35.0
        elif net_edge < 15.0:
            trap_score += 15.0

        if is_liquidity_trap:
            trap_score += 25.0
        elif min_volume is not None and min_volume < 300:
            trap_score += 10.0

        trap_risk_score = min(100.0, max(0.0, trap_score))

        # Opportunity Score (0-100)
        abs_z = abs(z_score) if z_score is not None else 0.0
        base_opp = min(70.0, (abs_z / 3.0) * 70.0)
        
        if net_edge > 0:
            net_bonus = min(30.0, (net_edge / 50.0) * 30.0)
            opp_score = base_opp + net_bonus
        else:
            opp_score = max(0.0, base_opp - 25.0)

        # Penalize opportunity score if trap risks are high
        if is_expiry_risk:
            opp_score = max(5.0, opp_score * 0.4)
        if is_liquidity_trap:
            opp_score = max(5.0, opp_score * 0.7)

        opportunity_score = round(min(100.0, max(0.0, opp_score)), 1)

        # Classification Hierarchy
        if is_expiry_risk:
            classification = "Expiry-Risk"
            reason = f"Lifecycle boundary alert: contract expires in {dte_min} days. Physical delivery and tender friction dominate spread."
        elif abs_z >= z_watch_threshold and is_cost_blocked:
            classification = "Cost-Blocked"
            reason = f"Gross edge of ₹{gross_edge}/10g is absorbed by estimated transaction hurdle of ₹{cost_hurdle}/10g (net edge: ₹{net_edge})."
        elif abs_z >= z_investigate_threshold and is_liquidity_trap:
            classification = "Watch"
            reason = f"Statistical dislocation (|Z|={abs_z:.2f}σ) detected, but secondary leg liquidity (Vol={min_volume}, OI={min_open_interest}) fails depth threshold."
        elif abs_z >= z_investigate_threshold and not liquidity_known:
            classification = "Watch"
            reason = f"Statistical dislocation (|Z|={abs_z:.2f}σ) detected, but liquidity is unassessed because volume or open interest was not supplied."
        elif abs_z >= z_investigate_threshold and net_edge > 0:
            classification = "Investigate"
            reason = f"Confirmed statistical dislocation (|Z|={abs_z:.2f}σ, Percentile={percentile:.1f}%) with positive net edge (₹{net_edge}/10g after friction)."
        elif abs_z >= z_watch_threshold:
            classification = "Watch"
            reason = f"Emerging spread drift (|Z|={abs_z:.2f}σ) under active observation."
        else:
            classification = "No Signal"
            reason = f"Spread is within normal historical equilibrium (|Z|={abs_z:.2f}σ < {z_watch_threshold}σ)."

        if not liquidity_known and "liquidity is unassessed" not in reason.lower():
            reason += " Liquidity is unassessed because volume or open interest was not supplied."

        return (
            classification,
            opportunity_score,
            round(trap_risk_score, 1),
            is_expiry_risk,
            is_cost_blocked,
            is_liquidity_trap,
            gross_edge,
            net_edge,
            reason
        )

    def get_radar_summary(
        self,
        window_days: int = 30,
        evaluation_date: Optional[date] = None
    ) -> RadarResponse:
        """
        Generates the 6-pair relative-value radar matrix for the latest available date
        (or a specified evaluation_date).
        """
        cost_hurdle = calculate_cost_hurdle().total_roundtrip_cost_per_10g

        items: List[PairRadarItem] = []
        investigate_count = 0
        cost_blocked_count = 0
        expiry_risk_count = 0
        watch_count = 0

        latest_date = evaluation_date or eligible_analytics_observations_query(self.db).with_entities(
            func.max(MarketObservation.trade_date)
        ).scalar()

        for leg_a, leg_b in VALID_PAIRS:
            pair_name = f"{leg_a}-{leg_b}"
            series_resp = self.calculate_pairwise_spread_series(
                leg_a=leg_a,
                leg_b=leg_b,
                window_days=window_days,
                end_date=latest_date
            )
            full_pair_history = series_resp.data_points

            # A snapshot is only comparable when every pair uses the same session.
            # Missing pair observations remain empty instead of carrying stale data.
            if latest_date is not None:
                series_resp.data_points = [point for point in series_resp.data_points if point.trade_date == latest_date]

            if not series_resp.data_points:
                # Explain why this pair has no point on the common snapshot date.
                reason = "No eligible synchronized observations are available for this pair."
                if latest_date is not None:
                    latest_rows = eligible_analytics_observations_query(self.db).filter(
                        MarketObservation.symbol.in_((leg_a, leg_b)),
                        MarketObservation.trade_date == latest_date
                    ).all()
                    expiries_by_symbol = {
                        symbol: sorted({row.expiry_date for row in latest_rows if row.symbol == symbol and row.expiry_date})
                        for symbol in (leg_a, leg_b)
                    }
                    expiries_a, expiries_b = expiries_by_symbol[leg_a], expiries_by_symbol[leg_b]
                    if expiries_a and expiries_b and not set(expiries_a).intersection(expiries_b):
                        fmt = lambda values: ", ".join(value.isoformat() for value in values)
                        reason = (
                            f"No same-expiry contracts for {pair_name} on evaluation date {latest_date}; "
                            f"{leg_a} expiries: {fmt(expiries_a)}; {leg_b} expiries: {fmt(expiries_b)}. "
                            "Different expiries are not paired."
                        )
                    elif not expiries_a or not expiries_b:
                        missing = leg_a if not expiries_a else leg_b
                        reason = f"No {missing} observation is available on evaluation date {latest_date}."
                    if full_pair_history:
                        latest_match = full_pair_history[-1]
                        reason += (
                            f" Latest exact shared-expiry history: {latest_match.trade_date} "
                            f"(expiry {latest_match.expiry_date}; {len(full_pair_history)} observations); "
                            "it is not a current snapshot."
                        )
                items.append(PairRadarItem(
                    pair=pair_name,
                    leg_a=leg_a,
                    leg_b=leg_b,
                    trade_date=None,
                    expiry_date=None,
                    spread=None,
                    rolling_mean=None,
                    rolling_std=None,
                    z_score=None,
                    percentile_rank=None,
                    deviation_intensity=None,
                    historical_norm=None,
                    friction_boundary=None,
                    classification="No Signal",
                    opportunity_score=None,
                    trap_risk_score=None,
                    is_expiry_risk=False,
                    is_cost_blocked=False,
                    is_liquidity_trap=False,
                    dte_min=None,
                    min_volume=None,
                    min_open_interest=None,
                    estimated_cost_hurdle=cost_hurdle,
                    gross_edge=None,
                    net_edge=None,
                    reason=reason
                ))
                continue

            last_pt = series_resp.data_points[-1]
            if latest_date is None or last_pt.trade_date > latest_date:
                latest_date = last_pt.trade_date

            dte_min = None
            if last_pt.dte_a is not None and last_pt.dte_b is not None:
                dte_min = min(last_pt.dte_a, last_pt.dte_b)
            elif last_pt.dte_a is not None:
                dte_min = last_pt.dte_a
            elif last_pt.dte_b is not None:
                dte_min = last_pt.dte_b

            min_vol = min(last_pt.volume_a, last_pt.volume_b) if last_pt.volume_a is not None and last_pt.volume_b is not None else None
            min_oi = min(last_pt.open_interest_a, last_pt.open_interest_b) if last_pt.open_interest_a is not None and last_pt.open_interest_b is not None else None

            (
                classification,
                opp_score,
                trap_score,
                is_exp,
                is_cost,
                is_liq,
                gross_edge,
                net_edge,
                reason
            ) = self.classify_relative_value_state(
                spread=last_pt.spread,
                rolling_mean=last_pt.rolling_mean,
                z_score=last_pt.z_score,
                percentile=last_pt.percentile_rank,
                dte_min=dte_min,
                min_volume=min_vol,
                min_open_interest=min_oi,
                cost_hurdle=cost_hurdle
            )

            if classification == "Investigate":
                investigate_count += 1
            elif classification == "Cost-Blocked":
                cost_blocked_count += 1
            elif classification == "Expiry-Risk":
                expiry_risk_count += 1
            elif classification == "Watch":
                watch_count += 1

            # Map Z to 0-100 radar deviation intensity
            abs_z = abs(last_pt.z_score) if last_pt.z_score is not None else None
            dev_intensity = round(min(100.0, (abs_z / 2.5) * 100.0), 1) if abs_z is not None else None
            prior_intensities = [
                min(100.0, abs(point.z_score) / 2.5 * 100.0)
                for point in full_pair_history
                if point.trade_date < last_pt.trade_date and point.z_score is not None
            ]
            historical_norm = round(float(np.median(prior_intensities)), 1) if prior_intensities else None
            friction_boundary = (
                round(min(100.0, cost_hurdle / last_pt.rolling_std / 2.5 * 100.0), 1)
                if last_pt.rolling_std is not None and last_pt.rolling_std > 0
                else None
            )

            items.append(PairRadarItem(
                pair=pair_name,
                leg_a=leg_a,
                leg_b=leg_b,
                trade_date=last_pt.trade_date,
                expiry_date=last_pt.expiry_date,
                spread=last_pt.spread,
                rolling_mean=last_pt.rolling_mean,
                rolling_std=last_pt.rolling_std,
                z_score=last_pt.z_score,
                percentile_rank=last_pt.percentile_rank,
                deviation_intensity=dev_intensity,
                historical_norm=historical_norm,
                friction_boundary=friction_boundary,
                classification=classification,
                opportunity_score=opp_score,
                trap_risk_score=trap_score,
                is_expiry_risk=is_exp,
                is_cost_blocked=is_cost,
                is_liquidity_trap=is_liq,
                dte_min=dte_min,
                min_volume=min_vol,
                min_open_interest=min_oi,
                estimated_cost_hurdle=cost_hurdle,
                gross_edge=gross_edge,
                net_edge=net_edge,
                reason=reason
            ))

        return RadarResponse(
            evaluation_date=latest_date,
            window_days=window_days,
            pairs=items,
            active_investigations_count=investigate_count,
            cost_blocked_count=cost_blocked_count,
            expiry_risk_count=expiry_risk_count,
            watch_count=watch_count
        )

    def get_events(
        self,
        status: Optional[str] = None,
        pair: Optional[str] = None,
        min_z: Optional[float] = None,
        limit: int = 50,
        offset: int = 0
    ) -> EventsResponse:
        """
        Retrieves detected relative-value events across history, with complete audit trail.
        """
        cost_hurdle = calculate_cost_hurdle().total_roundtrip_cost_per_10g
        target_pairs = VALID_PAIRS
        if pair:
            try:
                la, lb, inv = parse_pair(pair)
                target_pairs = [(la, lb)]
            except ValueError:
                target_pairs = []

        all_events: List[RelativeValueEvent] = []

        for leg_a, leg_b in target_pairs:
            series = self.calculate_pairwise_spread_series(leg_a, leg_b, window_days=30)
            pair_name = f"{leg_a}-{leg_b}"

            for idx, pt in enumerate(series.data_points):
                if pt.z_score is None:
                    continue
                
                abs_z = abs(pt.z_score)
                if min_z and abs_z < min_z:
                    continue

                dte_min = min(pt.dte_a, pt.dte_b) if (pt.dte_a and pt.dte_b) else (pt.dte_a or pt.dte_b)
                min_vol = min(pt.volume_a, pt.volume_b) if pt.volume_a is not None and pt.volume_b is not None else None
                min_oi = min(pt.open_interest_a, pt.open_interest_b) if pt.open_interest_a is not None and pt.open_interest_b is not None else None

                (
                    classification,
                    opp_score,
                    trap_score,
                    is_exp,
                    is_cost,
                    is_liq,
                    gross_edge,
                    net_edge,
                    reason
                ) = self.classify_relative_value_state(
                    spread=pt.spread,
                    rolling_mean=pt.rolling_mean,
                    z_score=pt.z_score,
                    percentile=pt.percentile_rank,
                    dte_min=dte_min,
                    min_volume=min_vol,
                    min_open_interest=min_oi,
                    cost_hurdle=cost_hurdle
                )

                if status and classification.lower() != status.lower():
                    continue

                # Severity calculation
                if abs_z >= 2.0 and classification == "Investigate":
                    severity = "critical"
                elif abs_z >= 1.5 or classification in ("Investigate", "Cost-Blocked"):
                    severity = "high"
                elif abs_z >= 1.0 or classification == "Watch":
                    severity = "medium"
                else:
                    severity = "low"

                event_id = f"EVT-{pt.trade_date.strftime('%Y%m%d')}-{leg_a[:3]}{leg_b[:3]}-{idx+1:03d}"

                caveats = []
                if is_exp:
                    caveats.append(f"Near expiry delivery risk: contract within {dte_min} days of expiry.")
                if is_cost:
                    caveats.append(f"Transaction friction hurdle: gross edge ₹{gross_edge} is smaller than friction hurdle ₹{cost_hurdle}.")
                if is_liq:
                    caveats.append(f"Thin volume / open interest in secondary leg (Vol: {min_vol}, OI: {min_oi}).")

                all_events.append(RelativeValueEvent(
                    event_id=event_id,
                    pair=pair_name,
                    leg_a=leg_a,
                    leg_b=leg_b,
                    trade_date=pt.trade_date,
                    severity=severity,
                    classification=classification,
                    opportunity_score=opp_score,
                    trap_risk_score=trap_score,
                    summary=f"{pair_name} spread reached ₹{pt.spread:+.2f}/10g (Z={pt.z_score:+.2f}σ, {pt.percentile_rank:.1f}th pct). Classification: {classification}.",
                    evidence=EventEvidenceTrail(
                        spread=pt.spread,
                        benchmark_basis="₹ per 10g (995 fine gold equivalent)",
                        rolling_mean=pt.rolling_mean,
                        rolling_std=pt.rolling_std,
                        z_score=pt.z_score,
                        percentile_rank=pt.percentile_rank,
                        gross_edge=gross_edge,
                        net_edge=net_edge,
                        dte_a=pt.dte_a,
                        dte_b=pt.dte_b,
                        volume_a=pt.volume_a,
                        volume_b=pt.volume_b,
                        open_interest_a=pt.open_interest_a,
                        open_interest_b=pt.open_interest_b,
                        cost_hurdle=cost_hurdle,
                        rule_triggered=reason,
                        caveats=caveats
                    )
                ))

        # Sort descending by trade_date then opportunity_score
        all_events.sort(key=lambda e: (e.trade_date, e.opportunity_score), reverse=True)
        total = len(all_events)
        paged = all_events[offset : offset + limit]

        return EventsResponse(total_events=total, items=paged)

    def get_spread_distribution(
        self,
        pair: str,
        window_days: int = 365,
        num_bins: int = 15
    ) -> DistributionResponse:
        """
        Calculates empirical distribution and Gaussian theoretical normal curve
        for the specified pair over the available history. Each point pairs the
        same trade date and expiry; when multiple shared expiries exist, the
        nearest shared expiry is selected for that session. Expiry can therefore
        roll between historical points, but never within one paired observation.
        """
        try:
            leg_a, leg_b, is_inverted = parse_pair(pair)
        except ValueError:
            return DistributionResponse(
                pair=pair,
                window_days=window_days,
                sample_size=0,
                bins=[],
                frequencies=[],
                gaussian_pdf=[],
                status="invalid_pair"
            )

        series = self.calculate_pairwise_spread_series(leg_a, leg_b, window_days=window_days, invert_spread=is_inverted)
        if not series.data_points:
            return DistributionResponse(
                pair=pair,
                window_days=window_days,
                sample_size=0,
                bins=[],
                frequencies=[],
                gaussian_pdf=[],
                status="insufficient_history"
            )

        # `window_days` is the existing API parameter name; distribution windows
        # are bounded by synchronized trading observations, not calendar dates.
        points = series.data_points[-window_days:]
        spreads = [p.spread for p in points]
        sample_size = len(spreads)
        current_spread = spreads[-1]
        last_point = points[-1]

        mean_val = float(np.mean(spreads))
        sigma_val = float(np.std(spreads, ddof=1)) if sample_size > 1 else 0.0
        median_val = float(np.median(spreads))

        # Skewness and kurtosis
        skew_val = 0.0
        kurt_val = 3.0
        if sigma_val > 1e-6 and sample_size >= 3:
            norm_dev = [(x - mean_val) / sigma_val for x in spreads]
            skew_val = float(np.mean([d**3 for d in norm_dev]))
            kurt_val = float(np.mean([d**4 for d in norm_dev]))

        kurt_str = f"{kurt_val:.2f} ({'Fat Tails' if kurt_val > 3.2 else 'Standard'})"
        skew_str = f"{skew_val:+.2f}"
        cur_z_str = f"{last_point.z_score:+.2f}σ ({last_point.percentile_rank:.1f}%)" if last_point.z_score is not None else "N/A"

        # Construct histogram bins centered around data range or default visual bins
        min_s, max_s = min(spreads), max(spreads)
        if min_s == max_s:
            min_s -= 10
            max_s += 10

        # Create clean bins
        bin_edges = np.linspace(min_s, max_s, num_bins + 1)
        freqs, _ = np.histogram(spreads, bins=bin_edges)
        bin_centers = [round(float((bin_edges[i] + bin_edges[i+1]) / 2.0), 1) for i in range(num_bins)]

        # Generate Gaussian theoretical normal fit evaluated at bin centers
        gaussian_pdf: List[float] = []
        if sigma_val > 1e-6:
            for x in bin_centers:
                exponent = -0.5 * ((x - mean_val) / sigma_val) ** 2
                pdf_val = (1.0 / (sigma_val * math.sqrt(2 * math.pi))) * math.exp(exponent)
                # Scale PDF to match histogram area
                bin_width = bin_edges[1] - bin_edges[0]
                scaled = pdf_val * sample_size * bin_width
                gaussian_pdf.append(round(float(scaled), 2))
        else:
            gaussian_pdf = [0.0] * num_bins

        return DistributionResponse(
            pair=pair,
            window_days=window_days,
            sample_size=sample_size,
            expiry_policy=(
                "Each point matches the same trade date and expiry; the nearest "
                "shared expiry is selected per session, so expiry can roll across history."
            ),
            evaluation_date=last_point.trade_date,
            expiry_date=last_point.expiry_date,
            mean=round(mean_val, 2),
            sigma=round(sigma_val, 2),
            median=round(median_val, 2),
            skewness=round(skew_val, 2),
            kurtosis=kurt_str,
            current_spread=round(current_spread, 2),
            current_z_score=cur_z_str,
            bins=bin_centers,
            frequencies=[int(f) for f in freqs],
            gaussian_pdf=gaussian_pdf,
            status="valid"
        )
