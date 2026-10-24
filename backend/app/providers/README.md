# Authorized MCX provider bridge

AURORA does not assume MCX offers a generic authenticated REST endpoint. MCX's
direct feed has its own contracted specifications and delivery arrangements.
The backend adapter currently accepts an HTTPS bridge provided by the contracted
MCX data distributor. Obtain written rights for AURORA's processing, persistence,
and display use before enabling it. This adapter does not grant those rights.

## Configuration

Set these server-side values in the project-root `.env`:

```dotenv
DATA_MODE=live_feed_authorized
MCX_FEED_BASE_URL=https://<authorized-provider-bridge-host>/<base-path>/
MCX_FEED_QUOTES_PATH=/quotes
MCX_FEED_API_KEY=<provider-issued-key>
MCX_FEED_API_SECRET=<provider-issued-secret>
MCX_FEED_PROVIDER_NAME=<contracted-provider-name>
MCX_FEED_LICENSE_CONFIRMED=true
MCX_FEED_TIMEOUT_SECONDS=5
MCX_FEED_LIVE_MAX_AGE_SECONDS=90
MCX_FEED_DELAYED_MAX_AGE_SECONDS=1800
MCX_FEED_POLL_INTERVAL_SECONDS=5
```

Only set `MCX_FEED_LICENSE_CONFIRMED=true` after verifying the agreement covers
the actual AURORA deployment. This setting is an operator attestation, not an
automated license check. Use only a provider endpoint whose vendor contract
permits these server-side `X-API-Key` and `X-API-Secret` headers.

## Bridge HTTP contract

The adapter makes `GET {MCX_FEED_BASE_URL}{MCX_FEED_QUOTES_PATH}` with JSON accept
headers and the two credential headers. The response must be JSON shaped like:

```json
{
  "authenticated": true,
  "exchange": "MCX",
  "feed_type": "live",
  "observations": [
    {
      "exchange": "MCX",
      "symbol": "GOLDM",
      "expiry_date": "2026-12-28",
      "timestamp": "2026-10-22T10:15:00+05:30",
      "last_price": 62500.0,
      "open_price": 62400.0,
      "high_price": 62600.0,
      "low_price": 62300.0,
      "volume": 120,
      "open_interest": 450
    }
  ]
}
```

`feed_type` must identify `live`/`realtime` or one of the delayed modes (`delayed`,
`delayed_1m`, `delayed_2m`, `delayed_5m`, `delayed_10m`, `delayed_15m`,
`delayed_20m`). Timestamps must be ISO-8601 and timezone-aware. Contract symbols
must already exist in the AURORA contract table; expiry is explicit and never
guessed. Price, OHLC, volume and open interest are validated before normalization.

The adapter polls on market-status or market-price requests and rate-limits calls
to the configured interval per process. It will not persist a provider observation
over a CSV or other non-provider observation for the same symbol/date/expiry.
Because the existing observation schema has one row per symbol/date/expiry, repeat
provider snapshots update that daily provider row only when their timestamp is
newer. This is not a tick archive. Confirm that the provider agreement permits
this daily persistence model before enabling storage.

Authentication credentials are sent only from the backend; responses never echo
them. Provider exceptions and HTTP bodies are not logged or returned to callers.
