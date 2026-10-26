# Free live MCX data integration — implementation notes

## Current AURORA state

AURORA already has a provider interface and an authorized-distributor HTTPS bridge:
- `backend/app/providers/base.py`
- `backend/app/providers/live_mock.py` (despite its historical filename, this is the authorized-provider adapter)
- `backend/app/providers/__init__.py`
- `backend/app/config.py`
- `backend/app/api/market.py`

The bridge is intentionally not a generic broker adapter. It expects a provider endpoint returning AURORA's documented JSON payload. Do not point it at a broker's API endpoint unless that endpoint implements the bridge contract.

## Zero-cost broker candidate: Angel One SmartAPI

Official docs:
- FAQ: https://smartapi.angelone.in/faq
- API docs: https://smartapi.angelbroking.com/docs
- Official Python SDK: https://github.com/angel-one/smartapi-python

The official FAQ states SmartAPI is free, supports historical commodity data, and offers live WebSocket prices. Its live market-data FULL mode documents volume and open interest. The API docs list MCX as a supported historical-data exchange. This makes it a reasonable candidate to test first, not a guarantee that every instrument or entitlement is enabled for every account.

## Safe implementation sequence

1. Create/enable a SmartAPI app through the broker's official portal and confirm MCX segment access.
2. Obtain the current instrument master from the official SmartAPI instrument source; map each AURORA contract to the correct MCX exchange token and explicit expiry. Never guess or hardcode a token across expiries.
3. Implement a dedicated SmartAPI adapter. It must handle login/session expiry, WebSocket reconnects, subscription failures, binary tick parsing, rate limits, and graceful shutdown. Keep all API keys, JWT/feed tokens, TOTP secrets and account identifiers server-side in environment variables; never commit them or expose them in API responses.
4. Normalize incoming ticks into AURORA's existing contract model and data-provenance rules. Preserve exchange timestamps; mark volume/OI as unavailable when not actually supplied.
5. Test against a paper/test account session and recorded fixture payloads before enabling it in the active provider factory.
6. Only mark the feed LIVE when authenticated MCX data is actually arriving and timestamps pass the configured freshness check. Show STALE/OFFLINE otherwise.

## Important limitations

- A free API plan is not the same as permission to redistribute exchange data. Confirm the broker's terms for the intended display/storage use.
- AURORA's current `MarketObservation` schema is daily-grain (one row per symbol/trade date/expiry); it is not a tick archive. For intraday analytics, use a separate tick/snapshot table or explicitly document the snapshot cadence rather than pretending daily rows are a tick history.
- Do not create fake live prices or silently relabel historical/bhavcopy observations as live.
- No API credentials are required in GitHub. Configure local secrets only in the untracked project-root `.env`.
