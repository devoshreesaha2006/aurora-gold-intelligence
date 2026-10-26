"""Minimal server-side SmartAPI FULL-quote client for AURORA.

This module only fetches quote payloads. It deliberately does not claim that a
feed is connected, persist observations, or place orders. Keep all session tokens
server-side and configure them only in the untracked project-root .env.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

import httpx


SMARTAPI_QUOTE_URL = (
    "https://apiconnect.angelone.in/rest/secure/angelbroking/market/v1/quote/"
)


class SmartAPIError(RuntimeError):
    """Sanitized SmartAPI request/response error."""


class SmartAPIMarketDataClient:
    """Fetch FULL quotes for known MCX instrument tokens using an active session."""

    def __init__(
        self,
        *,
        api_key: str,
        jwt_token: str,
        client_code: str,
        local_ip: str,
        public_ip: str,
        mac_address: str,
        timeout_seconds: float = 5.0,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        required = {
            "api_key": api_key,
            "jwt_token": jwt_token,
            "client_code": client_code,
            "local_ip": local_ip,
            "public_ip": public_ip,
            "mac_address": mac_address,
        }
        missing = [name for name, value in required.items() if not str(value or "").strip()]
        if missing:
            raise ValueError("Missing SmartAPI configuration: " + ", ".join(missing))
        self.api_key = api_key
        self.jwt_token = jwt_token
        self.client_code = client_code
        self.local_ip = local_ip
        self.public_ip = public_ip
        self.mac_address = mac_address
        self.timeout_seconds = timeout_seconds
        self._client = http_client
        self._owns_client = http_client is None

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def _http_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout_seconds, follow_redirects=False)
        return self._client

    def fetch_full_mcx_quotes(self, tokens: Iterable[str]) -> List[Dict[str, Any]]:
        """Fetch FULL market data for up to 50 MCX tokens per request.

        Tokens must come from the current official SmartAPI instrument master;
        this method never guesses symbols or expiry dates. SmartAPI documents a
        limit of 50 symbols/request and one request/second for this endpoint.
        """
        clean_tokens = list(dict.fromkeys(str(token).strip() for token in tokens if str(token).strip()))
        if not clean_tokens:
            return []
        if len(clean_tokens) > 50:
            raise ValueError("SmartAPI quote requests support at most 50 tokens")
        headers = {
            "Authorization": "Bearer " + self.jwt_token,
            "X-PrivateKey": self.api_key,
            "X-UserType": "USER",
            "X-SourceID": "WEB",
            "X-ClientLocalIP": self.local_ip,
            "X-ClientPublicIP": self.public_ip,
            "X-MACAddress": self.mac_address,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            response = self._http_client().post(
                SMARTAPI_QUOTE_URL,
                headers=headers,
                json={"mode": "FULL", "exchangeTokens": {"MCX": clean_tokens}},
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            # Never include response bodies or headers: they can contain sensitive data.
            raise SmartAPIError("SmartAPI market-data request failed") from exc
        if not isinstance(payload, dict) or payload.get("status") is not True:
            raise SmartAPIError("SmartAPI did not confirm a successful market-data response")
        data = payload.get("data") or {}
        fetched = data.get("fetched", []) if isinstance(data, dict) else []
        if not isinstance(fetched, list):
            raise SmartAPIError("SmartAPI returned an unexpected quote payload")
        # Return only actual fetched quotes; missing tokens remain missing, never synthesized.
        return [item for item in fetched if isinstance(item, dict) and str(item.get("exchange", "")).upper() == "MCX"]
