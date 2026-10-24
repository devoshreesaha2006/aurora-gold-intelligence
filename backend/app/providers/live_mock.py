"""Authorized MCX distributor bridge adapter.

MCX does not expose a generic REST quote API. This adapter therefore consumes an
authorized distributor's HTTPS bridge using the documented AURORA payload contract
in README.md. It remains unavailable until the bridge authenticates and returns
validated, timestamped MCX observations.
"""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from hashlib import sha256
from math import isfinite
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.contract import Contract
from backend.app.models.market_observation import MarketObservation
from backend.app.providers.base import MarketDataProvider
from backend.app.schemas.market import MarketStatusRead
from backend.app.services.normalization import normalize_price


IST = ZoneInfo("Asia/Kolkata")
LIVE_FEED_TYPES = {"live", "realtime", "real_time"}
DELAYED_FEED_TYPES = {"delayed", "delayed_1m", "delayed_2m", "delayed_5m", "delayed_10m", "delayed_15m", "delayed_20m"}


class FeedPayloadError(ValueError):
    pass


class AuthorizedMCXLiveProvider(MarketDataProvider):
    """Poll an authorized provider bridge; do not infer feed health from config."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        base_url: Optional[str] = None,
        *,
        provider_name: Optional[str] = None,
        quotes_path: Optional[str] = None,
        license_confirmed: Optional[bool] = None,
        timeout_seconds: Optional[float] = None,
        live_max_age_seconds: Optional[int] = None,
        delayed_max_age_seconds: Optional[int] = None,
        poll_interval_seconds: Optional[int] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.mcx_feed_api_key
        self.api_secret = api_secret if api_secret is not None else settings.mcx_feed_api_secret
        self.base_url = base_url if base_url is not None else settings.mcx_feed_base_url
        self.provider_name = provider_name or settings.mcx_feed_provider_name
        self.quotes_path = quotes_path or settings.mcx_feed_quotes_path
        self.license_confirmed = settings.mcx_feed_license_confirmed if license_confirmed is None else license_confirmed
        self.timeout_seconds = timeout_seconds or settings.mcx_feed_timeout_seconds
        self.live_max_age_seconds = live_max_age_seconds or settings.mcx_feed_live_max_age_seconds
        self.delayed_max_age_seconds = delayed_max_age_seconds or settings.mcx_feed_delayed_max_age_seconds
        self.poll_interval_seconds = poll_interval_seconds or settings.mcx_feed_poll_interval_seconds
        self._client = http_client
        self._owns_client = http_client is None
        self._last_poll_at: Optional[datetime] = None
        self._last_poll_ok = False
        self._last_observation_received_at: Optional[datetime] = None
        self._last_provider_timestamp: Optional[datetime] = None
        self._last_feed_type: Optional[str] = None
        self._authentication_state = "unknown"
        self._connection_state = "disconnected"
        self._provider_error: Optional[str] = None
        self._retry_after: Optional[datetime] = None
        self._poll_lock = Lock()
        self._provider_key = sha256(self.provider_name.encode("utf-8")).hexdigest()[:10]

    def _http_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout_seconds, follow_redirects=False)
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def get_provider_name(self) -> str:
        return self.provider_name

    def is_live_connected(self) -> bool:
        now = datetime.now(timezone.utc)
        return bool(
            self._last_poll_ok
            and self._last_feed_type in LIVE_FEED_TYPES
            and self._last_provider_timestamp is not None
            and 0 <= (now - self._last_provider_timestamp).total_seconds() <= self.live_max_age_seconds
        )

    def _credentials_ready(self) -> bool:
        if not (
            self.license_confirmed and self.api_key and self.api_secret and self.base_url
        ):
            return False
        parsed = urlparse(self.base_url)
        if parsed.scheme != "https":
            # Permit plain HTTP only for loopback bridge development.
            return parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        return bool(parsed.hostname)

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime:
        if not isinstance(value, str) or not value.strip():
            raise FeedPayloadError("Observation is missing its provider timestamp")
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise FeedPayloadError("Observation has an invalid provider timestamp") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise FeedPayloadError("Provider timestamps must include a timezone offset")
        parsed = parsed.astimezone(timezone.utc)
        if parsed > datetime.now(timezone.utc) + timedelta(minutes=2):
            raise FeedPayloadError("Provider timestamp is unexpectedly in the future")
        return parsed

    @staticmethod
    def _number(value: Any, field: str, *, required: bool = False, minimum: float = 0) -> Optional[float]:
        if value is None and not required:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError) as exc:
            raise FeedPayloadError(f"Observation has an invalid {field}") from exc
        if not isfinite(number) or number < minimum:
            raise FeedPayloadError(f"Observation has an invalid {field}")
        return number

    def _normalize_quote(self, quote: Dict[str, Any], feed_type: str, contracts: Dict[str, Contract]) -> Tuple[MarketObservation, datetime]:
        if str(quote.get("exchange", "")).upper() != "MCX":
            raise FeedPayloadError("Observation exchange must be MCX")
        symbol = str(quote.get("symbol", "")).strip().upper()
        contract = contracts.get(symbol)
        if contract is None or not contract.is_active:
            raise FeedPayloadError("Observation symbol is not a configured active AURORA contract")
        expiry_value = quote.get("expiry_date")
        try:
            expiry = date.fromisoformat(str(expiry_value))
        except (TypeError, ValueError) as exc:
            raise FeedPayloadError("Observation has an invalid or missing expiry date") from exc

        provider_timestamp = self._parse_timestamp(quote.get("timestamp"))
        trade_date = provider_timestamp.astimezone(IST).date()
        if expiry < trade_date:
            raise FeedPayloadError("Observation expiry is earlier than its provider trade date")

        price = self._number(quote.get("last_price", quote.get("close_price")), "last price", required=True, minimum=0.000001)
        open_price = self._number(quote.get("open_price", quote.get("open")), "open price")
        high_price = self._number(quote.get("high_price", quote.get("high")), "high price")
        low_price = self._number(quote.get("low_price", quote.get("low")), "low price")
        volume_observed = quote.get("volume") is not None
        open_interest_value = quote.get("open_interest", quote.get("oi"))
        open_interest_observed = open_interest_value is not None
        volume = self._number(quote.get("volume") if volume_observed else 0, "volume", minimum=0)
        open_interest = self._number(open_interest_value if open_interest_observed else 0, "open interest", minimum=0)
        if volume is None or not volume.is_integer() or open_interest is None or not open_interest.is_integer():
            raise FeedPayloadError("Volume and open interest must be non-negative integers")
        if high_price is not None and high_price < max(price, open_price or price):
            raise FeedPayloadError("Observation high price is below the open or last price")
        if low_price is not None and low_price > min(price, open_price or price):
            raise FeedPayloadError("Observation low price is above the open or last price")
        if high_price is not None and low_price is not None and high_price < low_price:
            raise FeedPayloadError("Observation high price is below its low price")

        normalized_per_gram, normalized_10g = normalize_price(price, contract.quote_unit_grams, contract.purity_factor)
        source = f"authorized_provider:{self._provider_key}:{'live' if feed_type in LIVE_FEED_TYPES else 'delayed'}"
        return MarketObservation(
            symbol=symbol,
            trade_date=trade_date,
            expiry_date=expiry,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=price,
            volume=int(volume),
            open_interest=int(open_interest),
            volume_observed=volume_observed,
            open_interest_observed=open_interest_observed,
            normalized_price_per_gram=normalized_per_gram,
            normalized_price_10g_basis=normalized_10g,
            data_source=source,
            is_synthetic=False,
            provider_timestamp=provider_timestamp,
            is_provider_verified=True,
        ), provider_timestamp

    def _persist(self, db: Session, observation: MarketObservation) -> bool:
        existing = db.query(MarketObservation).filter(
            MarketObservation.symbol == observation.symbol,
            MarketObservation.trade_date == observation.trade_date,
            MarketObservation.expiry_date == observation.expiry_date,
        ).first()
        if existing is not None:
            # Never overwrite user CSV or other provenance. Same-provider repeats
            # are idempotent and only the newest timestamp may update the daily row.
            if not str(existing.data_source or "").startswith(f"authorized_provider:{self._provider_key}:"):
                return False
            old_ts = existing.provider_timestamp
            if old_ts is not None and old_ts.tzinfo is None:
                old_ts = old_ts.replace(tzinfo=timezone.utc)
            if old_ts is not None and old_ts >= observation.provider_timestamp:
                return True
            for field in (
                "open_price", "high_price", "low_price", "close_price", "volume",
                "open_interest", "normalized_price_per_gram", "normalized_price_10g_basis",
                "volume_observed", "open_interest_observed", "data_source", "is_synthetic",
                "provider_timestamp", "is_provider_verified",
            ):
                setattr(existing, field, getattr(observation, field))
            existing.created_at = datetime.now(timezone.utc)
        else:
            db.add(observation)
        return True

    def poll_once(self, db: Session, *, force: bool = False) -> int:
        with self._poll_lock:
            return self._poll_once_unlocked(db, force=force)

    def _poll_once_unlocked(self, db: Session, *, force: bool = False) -> int:
        """Fetch, validate, normalize and persist one authorized bridge response."""
        now = datetime.now(timezone.utc)
        if not self._credentials_ready():
            self._last_poll_ok = False
            self._connection_state = "disconnected"
            self._authentication_state = "unknown"
            self._provider_error = "Provider endpoint, credentials, and license confirmation are required"
            return 0
        if not force and self._last_poll_at and (now - self._last_poll_at).total_seconds() < self.poll_interval_seconds:
            return 0
        if not force and self._retry_after and now < self._retry_after:
            return 0

        self._last_poll_at = now
        self._last_poll_ok = False
        self._connection_state = "disconnected"
        self._provider_error = None
        url = urljoin(self.base_url.rstrip("/") + "/", self.quotes_path.lstrip("/"))
        headers = {
            "Accept": "application/json",
            "X-API-Key": self.api_key,
            "X-API-Secret": self.api_secret,
        }
        try:
            response = self._http_client().get(url, headers=headers, timeout=self.timeout_seconds)
            if response.status_code in (401, 403):
                self._authentication_state = "failed"
                self._provider_error = "Provider authentication failed"
                return 0
            if response.status_code == 429:
                self._provider_error = "Provider rate limit reached"
                retry_after = response.headers.get("Retry-After", "")
                try:
                    delay = max(1, min(int(retry_after), 300))
                except ValueError:
                    delay = max(1, self.poll_interval_seconds)
                self._retry_after = now + timedelta(seconds=delay)
                return 0
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException:
            self._provider_error = "Provider request timed out"
            return 0
        except (httpx.HTTPError, ValueError):
            self._provider_error = "Provider request failed"
            return 0

        if not isinstance(payload, dict) or payload.get("authenticated") is not True:
            self._authentication_state = "failed"
            self._provider_error = "Provider did not confirm authenticated access"
            return 0
        self._authentication_state = "authenticated"
        self._connection_state = "connected"
        feed_type = str(payload.get("feed_type", "")).strip().lower()
        if feed_type not in LIVE_FEED_TYPES | DELAYED_FEED_TYPES:
            self._provider_error = "Provider feed type is missing or unsupported"
            return 0
        observations = payload.get("observations")
        if not isinstance(observations, list) or not observations:
            self._provider_error = "Provider returned no observations"
            return 0

        contracts = {
            row.symbol.upper(): row
            for row in db.query(Contract).filter(Contract.is_active.is_(True)).all()
        }
        staged: List[MarketObservation] = []
        timestamps: List[datetime] = []
        try:
            for quote in observations:
                if not isinstance(quote, dict):
                    raise FeedPayloadError("Provider returned a malformed observation")
                observation, provider_ts = self._normalize_quote(quote, feed_type, contracts)
                staged.append(observation)
                timestamps.append(provider_ts)
        except FeedPayloadError as exc:
            self._provider_error = str(exc)
            return 0

        now = datetime.now(timezone.utc)
        freshness_limit = self.live_max_age_seconds if feed_type in LIVE_FEED_TYPES else self.delayed_max_age_seconds
        if any((now - timestamp).total_seconds() > freshness_limit for timestamp in timestamps):
            # Keep the stale source timestamp visible for status, but never feed an
            # expired quote into analytics or persist it as fresh provider data.
            self._last_provider_timestamp = max(timestamps)
            self._last_feed_type = feed_type
            self._connection_state = "connected"
            self._provider_error = "Stale provider observation rejected"
            return 0

        persisted_count = 0
        try:
            for observation in staged:
                if self._persist(db, observation):
                    persisted_count += 1
            if not persisted_count:
                db.rollback()
                self._provider_error = "Valid provider data conflicts with existing non-provider observations"
                return 0
            db.commit()
        except Exception:
            db.rollback()
            self._provider_error = "Could not persist provider observations"
            return 0

        self._last_poll_ok = True
        self._retry_after = None
        self._last_observation_received_at = datetime.now(timezone.utc)
        self._last_provider_timestamp = max(timestamps)
        self._last_feed_type = feed_type
        return persisted_count

    def _feed_status(self) -> Tuple[str, Optional[int]]:
        if not self._last_poll_ok or self._last_provider_timestamp is None:
            if self._last_provider_timestamp is not None:
                return "STALE", max(0, int((datetime.now(timezone.utc) - self._last_provider_timestamp).total_seconds()))
            return "UNAVAILABLE", None
        age = int((datetime.now(timezone.utc) - self._last_provider_timestamp).total_seconds())
        if age < 0:
            return "UNAVAILABLE", age
        if self._last_feed_type in LIVE_FEED_TYPES:
            return ("LIVE", age) if age <= self.live_max_age_seconds else ("STALE", age)
        return ("DELAYED", age) if age <= self.delayed_max_age_seconds else ("STALE", age)

    def get_market_status(self, db: Session) -> MarketStatusRead:
        self.poll_once(db)
        feed_status, freshness_seconds = self._feed_status()
        provider_rows = db.query(MarketObservation).filter(
            MarketObservation.is_provider_verified.is_(True),
            MarketObservation.is_synthetic.is_(False),
            MarketObservation.data_source.like(f"authorized_provider:{self._provider_key}:%"),
        )
        latest = provider_rows.order_by(MarketObservation.provider_timestamp.desc()).first()
        total_observations = provider_rows.count()
        latest_provider_ts = self._last_provider_timestamp or (latest.provider_timestamp if latest else None)
        received_at = self._last_observation_received_at or (latest.created_at if latest else None)
        if feed_status == "LIVE":
            mode, provenance = "live_feed_authorized", f"Verified authorized provider: {self.provider_name}"
            freshness_label = "Fresh timestamped MCX provider observations"
        elif feed_status == "DELAYED":
            mode, provenance = "delayed_feed_authorized", f"Authorized delayed MCX provider: {self.provider_name}"
            freshness_label = "Timestamped delayed MCX provider observations"
        elif feed_status == "STALE":
            mode, provenance = "live_feed_stale", f"Previously received authorized provider data: {self.provider_name}"
            freshness_label = "Last provider observation is stale"
        else:
            mode, provenance = "live_feed_disconnected", "No eligible authorized provider observation"
            freshness_label = self._provider_error or "Waiting for authenticated, timestamped MCX provider observations"
        if not self.license_confirmed:
            provenance = "Unverified configuration; provider license confirmation required"

        return MarketStatusRead(
            market_open=None,
            market_session_status="unknown",
            data_mode=mode,
            provider_name=self.get_provider_name(),
            is_live_connected=feed_status == "LIVE" and self._last_poll_ok,
            total_contracts_tracked=db.query(Contract).filter(Contract.is_active.is_(True)).count(),
            total_observations=total_observations,
            last_ingestion_at=received_at,
            latest_trade_date=latest.trade_date if latest else None,
            server_time=datetime.now(timezone.utc),
            data_freshness_label=freshness_label,
            feed_status=feed_status,
            connection_state=self._connection_state,
            authentication_state=self._authentication_state,
            last_observation_received_at=received_at,
            last_provider_timestamp=latest_provider_ts,
            feed_freshness_seconds=freshness_seconds,
            data_provenance=provenance,
            provider_error=self._provider_error,
        )

    def fetch_latest_observations(self, db: Session, limit: int = 100) -> List[MarketObservation]:
        self.poll_once(db)
        return (
            db.query(MarketObservation)
            .filter(
                MarketObservation.is_provider_verified.is_(True),
                MarketObservation.is_synthetic.is_(False),
                MarketObservation.data_source.like(f"authorized_provider:{self._provider_key}:%"),
            )
            .order_by(MarketObservation.provider_timestamp.desc())
            .limit(limit)
            .all()
        )
