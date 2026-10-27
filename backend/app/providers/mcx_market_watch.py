"""Opt-in importer for the public MCX Market Watch JSON endpoint.

This source is deliberately labelled unverified: a public webpage response is not
proof of a licensed feed or a guaranteed API contract. Keep disabled unless the
operator has checked MCX terms and deployment permissions.
"""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from math import isfinite
from threading import Lock
from typing import Any

import httpx
from sqlalchemy.orm import Session
from zoneinfo import ZoneInfo

from backend.app.config import settings
from backend.app.models.contract import Contract
from backend.app.models.market_observation import MarketObservation
from backend.app.providers.base import MarketDataProvider
from backend.app.schemas.market import MarketStatusRead
from backend.app.services.normalization import normalize_price

IST = ZoneInfo("Asia/Kolkata")
TARGETS = {"GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"}
SOURCE = "mcx_market_watch_public_unverified"


def _records(value: Any):
    """Walk response envelopes and yield quote-shaped dicts, regardless of wrapper key."""
    if isinstance(value, dict):
        if "Symbol" in value or "ProductCode" in value:
            yield value
        else:
            for child in value.values():
                yield from _records(child)
    elif isinstance(value, list):
        for child in value:
            yield from _records(child)


def _float(value: Any, *, required: bool = False):
    if value in (None, "") and not required:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(result):
        return None
    return result


def _timestamp(record: dict) -> datetime | None:
    raw = record.get("LTTValue") or record.get("LastTradeTime")
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.strptime(raw.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            parsed = datetime.fromisoformat(raw.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)
    return parsed.astimezone(timezone.utc)


def _expiry(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    for fmt in ("%d%b%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value.strip().upper(), fmt).date()
        except ValueError:
            pass
    return None


class MCXMarketWatchProvider(MarketDataProvider):
    """Best-effort public webpage importer; never represents itself as authenticated LIVE."""

    def __init__(self, http_client: httpx.Client | None = None):
        self._client = http_client or httpx.Client(timeout=settings.mcx_watch_timeout_seconds, follow_redirects=False)
        self._owns_client = http_client is None
        self._lock = Lock()
        self._last_poll: datetime | None = None
        self._last_received: datetime | None = None
        self._last_timestamp: datetime | None = None
        self._last_error: str | None = "Awaiting first Market Watch request"
        self._last_count = 0

    def close(self):
        if self._owns_client:
            self._client.close()

    def get_provider_name(self) -> str:
        return "MCX Market Watch (public endpoint; unverified)"

    def is_live_connected(self) -> bool:
        return False

    def _poll(self, db: Session, force: bool = False):
        now = datetime.now(timezone.utc)
        with self._lock:
            if not force and self._last_poll and (now - self._last_poll).total_seconds() < settings.mcx_watch_poll_interval_seconds:
                return
            self._last_poll = now
            self._last_error = None
            try:
                response = self._client.get(
                    settings.mcx_watch_url,
                    headers={"Accept": "application/json", "User-Agent": "AURORA-Commodity-Intelligence/1.0"},
                )
                response.raise_for_status()
                payload = response.json()
            except (httpx.HTTPError, ValueError):
                self._last_error = "MCX Market Watch endpoint request failed"
                return

            contracts = {
                c.symbol.upper(): c
                for c in db.query(Contract).filter(Contract.is_active.is_(True)).all()
                if c.symbol.upper() in TARGETS
            }
            staged: dict[tuple[str, date], MarketObservation] = {}
            rejected = 0
            for row in _records(payload):
                symbol = str(row.get("ProductCode") or row.get("Symbol") or "").strip().upper()
                if symbol not in TARGETS or str(row.get("InstrumentName", "")).upper() != "FUTCOM":
                    continue
                contract = contracts.get(symbol)
                expiry = _expiry(row.get("ExpiryDate"))
                stamp = _timestamp(row)
                price = _float(row.get("LTP"), required=True)
                opn, high, low = (_float(row.get(k)) for k in ("Open", "High", "Low"))
                volume = _float(row.get("Volume"), required=True)
                oi = _float(row.get("OpenInterest"), required=True)
                # Gold futures are orders of magnitude above ₹5; reject malformed
                # records and impossible OHLC rather than contaminating analytics.
                if (not contract or not expiry or not stamp or price is None or
                    price < 1000 or price > 10000000 or volume is None or oi is None or
                    volume < 0 or oi < 0 or not volume.is_integer() or not oi.is_integer() or
                    (high is not None and high < max(price, opn or price)) or
                    (low is not None and low > min(price, opn or price)) or
                    (high is not None and low is not None and high < low) or
                    expiry < stamp.astimezone(IST).date()):
                    rejected += 1
                    continue
                trade_date = stamp.astimezone(IST).date()
                norm_g, norm_10g = normalize_price(price, contract.quote_unit_grams, contract.purity_factor)
                obs = MarketObservation(
                    symbol=symbol, trade_date=trade_date, expiry_date=expiry,
                    open_price=opn, high_price=high, low_price=low, close_price=price,
                    volume=int(volume), open_interest=int(oi),
                    volume_observed=True, open_interest_observed=True,
                    normalized_price_per_gram=norm_g, normalized_price_10g_basis=norm_10g,
                    data_source=SOURCE, is_synthetic=False, is_provider_verified=False,
                    provider_timestamp=stamp,
                )
                key = (symbol, expiry)
                previous = staged.get(key)
                if previous is None or (previous.provider_timestamp or stamp) < stamp:
                    staged[key] = obs

            accepted = 0
            try:
                for obs in staged.values():
                    existing = db.query(MarketObservation).filter(
                        MarketObservation.symbol == obs.symbol,
                        MarketObservation.trade_date == obs.trade_date,
                        MarketObservation.expiry_date == obs.expiry_date,
                    ).first()
                    # Do not overwrite CSV imports or authorized-provider records.
                    if existing is not None and existing.data_source != SOURCE:
                        continue
                    if existing is not None:
                        old = existing.provider_timestamp
                        if old is not None and old.tzinfo is None:
                            old = old.replace(tzinfo=timezone.utc)
                        if old is not None and obs.provider_timestamp <= old:
                            accepted += 1
                            continue
                        for field in ("open_price", "high_price", "low_price", "close_price",
                                      "volume", "open_interest", "volume_observed", "open_interest_observed",
                                      "normalized_price_per_gram", "normalized_price_10g_basis", "provider_timestamp"):
                            setattr(existing, field, getattr(obs, field))
                        existing.created_at = now.replace(tzinfo=None)
                    else:
                        db.add(obs)
                    accepted += 1
                db.commit()
            except Exception:
                db.rollback()
                self._last_error = "Could not persist Market Watch observations"
                return
            fresh_rows = [o for o in staged.values() if o.provider_timestamp]
            if fresh_rows:
                self._last_timestamp = max(o.provider_timestamp for o in fresh_rows)
                self._last_received = now
            self._last_count = accepted
            if not staged:
                self._last_error = "No valid target FUTCOM gold futures found in Market Watch response"
            elif rejected:
                self._last_error = f"Rejected {rejected} malformed or implausible Market Watch quote(s)"

    def get_market_status(self, db: Session) -> MarketStatusRead:
        self._poll(db)
        now = datetime.now(timezone.utc)
        age = int((now - self._last_timestamp).total_seconds()) if self._last_timestamp else None
        stale_after = settings.mcx_watch_stale_after_seconds
        status = "UNAVAILABLE" if age is None else ("STALE" if age < 0 or age > stale_after else "UNVERIFIED")
        latest = db.query(MarketObservation).filter(
            MarketObservation.data_source == SOURCE,
        ).order_by(MarketObservation.provider_timestamp.desc()).first()
        return MarketStatusRead(
            market_open=None, market_session_status="unknown",
            data_mode="mcx_market_watch_unverified" if status == "UNVERIFIED" else "mcx_market_watch_stale" if status == "STALE" else "mcx_market_watch_unavailable",
            provider_name=self.get_provider_name(), is_live_connected=False,
            total_contracts_tracked=db.query(Contract).filter(Contract.is_active.is_(True)).count(),
            total_observations=db.query(MarketObservation).filter(MarketObservation.data_source == SOURCE).count(),
            last_ingestion_at=self._last_received, latest_trade_date=latest.trade_date if latest else None,
            server_time=now, data_freshness_label="Unverified public Market Watch snapshot" if status == "UNVERIFIED" else "Market Watch snapshot is stale or unavailable",
            feed_status=status, connection_state="connected" if self._last_timestamp else "disconnected",
            authentication_state="not_applicable_unverified", last_observation_received_at=self._last_received,
            last_provider_timestamp=self._last_timestamp, feed_freshness_seconds=age,
            data_provenance="Public MCX webpage endpoint; not an authenticated/licensed feed",
            provider_error=self._last_error,
        )

    def fetch_latest_observations(self, db: Session, limit: int = 100):
        self._poll(db)
        return db.query(MarketObservation).filter(
            MarketObservation.data_source == SOURCE,
        ).order_by(MarketObservation.provider_timestamp.desc()).limit(limit).all()
