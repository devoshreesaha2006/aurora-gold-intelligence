"""SmartAPI polling provider for explicitly mapped MCX gold contracts.

This adapter uses a manually provisioned short-lived JWT. It never logs credentials,
never guesses contract mappings, and only reports LIVE after receiving a fresh,
timestamped MCX quote from SmartAPI.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone, timedelta
from hashlib import sha256
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.contract import Contract
from backend.app.models.market_observation import MarketObservation
from backend.app.providers.base import MarketDataProvider
from backend.app.providers.smartapi_client import SmartAPIMarketDataClient, SmartAPIError
from backend.app.schemas.market import MarketStatusRead
from backend.app.services.normalization import normalize_price

IST = ZoneInfo("Asia/Kolkata")


class SmartAPIProvider(MarketDataProvider):
    def __init__(self):
        self._client: Optional[SmartAPIMarketDataClient] = None
        self._last_poll_at: Optional[datetime] = None
        self._last_received_at: Optional[datetime] = None
        self._last_provider_ts: Optional[datetime] = None
        self._last_error: Optional[str] = None
        self._last_ok = False
        self._poll_seconds = max(1, settings.smartapi_poll_interval_seconds)
        self._max_age = max(10, settings.smartapi_max_age_seconds)
        self._provider_key = sha256(b"angelone-smartapi").hexdigest()[:10]

    def get_provider_name(self) -> str:
        return "Angel One SmartAPI (MCX FULL quotes)"

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None

    def is_live_connected(self) -> bool:
        return bool(self._last_ok and self._last_provider_ts and
                    0 <= (datetime.now(timezone.utc) - self._last_provider_ts).total_seconds() <= self._max_age)

    def _mapping(self) -> List[dict]:
        try:
            raw = json.loads(settings.smartapi_mcx_token_map or "[]")
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(raw, list):
            return []
        clean = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            token, symbol, expiry = (str(item.get(k, "")).strip() for k in ("token", "symbol", "expiry_date"))
            try:
                date.fromisoformat(expiry)
            except ValueError:
                continue
            if token.isdigit() and symbol and symbol.replace("_", "").isalnum():
                clean.append({"token": token, "symbol": symbol.upper(), "expiry_date": expiry})
        # Duplicate token or duplicate contract mappings are ambiguous; reject the whole map.
        if len({x["token"] for x in clean}) != len(clean) or len({(x["symbol"], x["expiry_date"]) for x in clean}) != len(clean):
            return []
        return clean[:50]

    def _get_client(self) -> SmartAPIMarketDataClient:
        if self._client is None:
            self._client = SmartAPIMarketDataClient(
                api_key=settings.smartapi_api_key or "",
                jwt_token=settings.smartapi_jwt_token or "",
                client_code=settings.smartapi_client_code or "",
                local_ip=settings.smartapi_local_ip or "",
                public_ip=settings.smartapi_public_ip or "",
                mac_address=settings.smartapi_mac_address or "",
                timeout_seconds=settings.smartapi_timeout_seconds,
            )
        return self._client

    def poll_once(self, db: Session, force: bool = False) -> int:
        now = datetime.now(timezone.utc)
        if not force and self._last_poll_at and (now - self._last_poll_at).total_seconds() < self._poll_seconds:
            return 0
        self._last_poll_at = now
        self._last_ok = False
        mapping = self._mapping()
        if not settings.smartapi_license_confirmed:
            self._last_error = "Confirm broker data licensing/usage rights in local configuration first"
            return 0
        if not mapping:
            self._last_error = "Configure SMARTAPI_MCX_TOKEN_MAP with current MCX tokens and explicit AURORA symbols/expiry dates"
            return 0
        try:
            quotes = self._get_client().fetch_full_mcx_quotes([x["token"] for x in mapping])
        except (ValueError, SmartAPIError):
            self._last_error = "SmartAPI configuration/session/request failed; check local settings and session expiry"
            return 0
        by_token = {x["token"]: x for x in mapping}
        contracts = {c.symbol.upper(): c for c in db.query(Contract).filter(Contract.is_active.is_(True)).all()}
        accepted = []
        timestamps = []
        try:
            for q in quotes:
                token = str(q.get("symbolToken", "")).strip()
                m = by_token.get(token)
                if not m or str(q.get("exchange", "")).upper() != "MCX":
                    continue
                contract = contracts.get(m["symbol"])
                if not contract:
                    continue
                ts_raw = q.get("exchFeedTime") or q.get("exchTradeTime")
                ts = datetime.strptime(str(ts_raw), "%d-%b-%Y %H:%M:%S").replace(tzinfo=IST).astimezone(timezone.utc)
                age = (now - ts).total_seconds()
                if age < -120 or age > self._max_age:
                    continue
                trade_date = ts.astimezone(IST).date()
                expiry = date.fromisoformat(m["expiry_date"])
                if expiry < trade_date:
                    continue
                price = float(q["ltp"])
                if price <= 0:
                    continue
                def optional_price(key):
                    val = q.get(key)
                    return float(val) if val not in (None, "") and float(val) >= 0 else None
                vol = q.get("tradeVolume")
                oi = q.get("opnInterest")
                volume_observed = vol is not None
                oi_observed = oi is not None
                volume = int(float(vol or 0))
                open_interest = int(float(oi or 0))
                norm_g, norm_10g = normalize_price(price, contract.quote_unit_grams, contract.purity_factor)
                accepted.append(MarketObservation(
                    symbol=m["symbol"], trade_date=trade_date, expiry_date=expiry,
                    open_price=optional_price("open"), high_price=optional_price("high"),
                    low_price=optional_price("low"), close_price=price,
                    volume=volume, open_interest=open_interest,
                    volume_observed=volume_observed, open_interest_observed=oi_observed,
                    normalized_price_per_gram=norm_g, normalized_price_10g_basis=norm_10g,
                    data_source=f"smartapi:{self._provider_key}:live", is_synthetic=False,
                    provider_timestamp=ts, is_provider_verified=True,
                ))
                timestamps.append(ts)
        except (ValueError, TypeError, KeyError):
            self._last_error = "SmartAPI returned a quote with invalid fields or timestamp; rejected safely"
            return 0
        if not accepted:
            self._last_error = "No fresh MCX quotes matched the configured token-to-contract mapping"
            return 0
        try:
            saved = 0
            for obs in accepted:
                old = db.query(MarketObservation).filter(
                    MarketObservation.symbol == obs.symbol,
                    MarketObservation.trade_date == obs.trade_date,
                    MarketObservation.expiry_date == obs.expiry_date,
                ).first()
                if old and not str(old.data_source or "").startswith(f"smartapi:{self._provider_key}:"):
                    continue
                if old:
                    old_ts = old.provider_timestamp
                    if old_ts and old_ts.tzinfo is None:
                        old_ts = old_ts.replace(tzinfo=timezone.utc)
                    if old_ts and old_ts >= obs.provider_timestamp:
                        continue
                    for field in ("open_price", "high_price", "low_price", "close_price", "volume", "open_interest",
                                  "volume_observed", "open_interest_observed", "normalized_price_per_gram",
                                  "normalized_price_10g_basis", "provider_timestamp", "is_provider_verified", "data_source"):
                        setattr(old, field, getattr(obs, field))
                else:
                    db.add(obs)
                saved += 1
            db.commit()
            if saved == 0:
                self._last_error = "Quotes received, but existing non-SmartAPI records were preserved"
                return 0
        except Exception:
            db.rollback()
            self._last_error = "Could not persist SmartAPI observations"
            return 0
        self._last_ok = True
        self._last_received_at = datetime.now(timezone.utc)
        self._last_provider_ts = max(timestamps)
        self._last_error = None
        return saved

    def get_market_status(self, db: Session) -> MarketStatusRead:
        self.poll_once(db)
        age = int((datetime.now(timezone.utc) - self._last_provider_ts).total_seconds()) if self._last_provider_ts else None
        fresh = self.is_live_connected()
        rows = db.query(MarketObservation).filter(
            MarketObservation.data_source == f"smartapi:{self._provider_key}:live",
            MarketObservation.is_provider_verified.is_(True),
        )
        latest = rows.order_by(MarketObservation.provider_timestamp.desc()).first()
        return MarketStatusRead(
            market_open=None, market_session_status="unknown",
            data_mode="live_feed_authorized" if fresh else ("live_feed_stale" if latest else "live_feed_disconnected"),
            provider_name=self.get_provider_name(), is_live_connected=fresh,
            total_contracts_tracked=db.query(Contract).filter(Contract.is_active.is_(True)).count(),
            total_observations=rows.count(), last_ingestion_at=self._last_received_at or (latest.created_at if latest else None),
            latest_trade_date=latest.trade_date if latest else None, server_time=datetime.now(timezone.utc),
            data_freshness_label="Fresh timestamped SmartAPI MCX quotes" if fresh else (self._last_error or "Waiting for fresh broker quotes"),
            feed_status="LIVE" if fresh else ("STALE" if latest else "UNAVAILABLE"),
            connection_state="connected" if fresh else "disconnected",
            authentication_state="authenticated" if fresh else ("configured" if settings.smartapi_jwt_token else "not_configured"),
            last_observation_received_at=self._last_received_at or (latest.created_at if latest else None),
            last_provider_timestamp=self._last_provider_ts or (latest.provider_timestamp if latest else None),
            feed_freshness_seconds=age,
            data_provenance="Angel One SmartAPI; explicit MCX token mapping; broker quote timestamps" if fresh else "No verified fresh SmartAPI quote",
            provider_error=self._last_error,
        )

    def fetch_latest_observations(self, db: Session, limit: int = 100) -> List[MarketObservation]:
        self.poll_once(db)
        return rows_query(db, self._provider_key, limit)


def rows_query(db: Session, provider_key: str, limit: int) -> List[MarketObservation]:
    return db.query(MarketObservation).filter(
        MarketObservation.data_source == f"smartapi:{provider_key}:live",
        MarketObservation.is_provider_verified.is_(True),
    ).order_by(MarketObservation.provider_timestamp.desc()).limit(limit).all()
