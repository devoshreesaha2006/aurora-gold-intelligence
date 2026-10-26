# MCX live data integration — implementation notes

## Current AURORA state

AURORA has a provider interface and an authorized-distributor HTTPS bridge:
- `backend/app/providers/base.py`
- `backend/app/providers/live_mock.py` (despite its historical filename, this is the authorized-provider adapter)
- `backend/app/providers/__init__.py`
- `backend/app/config.py`
- `backend/app/api/market.py`

The bridge is intentionally not a generic broker adapter. It expects a provider endpoint returning AURORA's documented JSON payload. Do not point it at a broker's API endpoint unless that endpoint implements the bridge contract.

## Data access and licensing

No authenticated live MCX feed is currently configured by default. Contact a market-data distributor to confirm:
- MCX GOLD/GOLDM instruments and current contracts are included
- Live versus delayed data, historical coverage, and quote fields available
- API protocol, credentials, rate limits, and trial/pricing
- The license permits AURORA's intended processing, storage, and display

Keep credentials in the untracked project-root `.env`; never commit secrets or expose them in API responses.

## Safe integration sequence

1. Obtain written confirmation of data coverage and the applicable license.
2. Configure the distributor's HTTPS bridge to match the documented response contract.
3. Normalize incoming quotes into AURORA's existing contract model and data-provenance rules. Preserve source timestamps and mark unavailable volume/open interest as unavailable.
4. Only mark the feed LIVE when authenticated MCX data is actually arriving and timestamps pass the configured freshness check. Show STALE/OFFLINE otherwise.

## Important limitations

- A data API plan is not automatically permission to redistribute exchange data. Confirm the provider's terms for the intended display/storage use.
- AURORA's current `MarketObservation` schema is daily-grain (one row per symbol/trade date/expiry); it is not a tick archive. For intraday analytics, use a separate tick/snapshot table or explicitly document the snapshot cadence rather than pretending daily rows are a tick history.
- Do not create fake live prices or silently relabel historical/bhavcopy observations as live.
- No API credentials are required in GitHub. Configure local secrets only in the untracked project-root `.env`.
