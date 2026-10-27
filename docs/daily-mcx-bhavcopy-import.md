# Daily MCX Bhavcopy Import (gated)

This adapter is deliberately **disabled by default**. It does not guess an MCX download URL and does not scrape the Market Watch page. Configure it only after confirming that the selected source may be accessed automatically and that the intended storage/analytics/display use is permitted.

## Flow

1. A scheduled GitHub Actions workflow runs on weekdays at 18:00 IST.
2. It downloads a direct HTTPS file hosted on `mcxindia.com` or `www.mcxindia.com`.
3. It accepts either a CSV or an HTML table exported with an `.xls` extension (some spreadsheet downloads are HTML documents rather than binary Excel workbooks).
4. It maps the source columns to AURORA's canonical CSV schema, filters the four supported gold symbols, and submits that CSV to the existing `POST /api/data/upload` endpoint with `data_source=mcx_bhavcopy_official_csv`.
   - Trade and expiry dates are normalized to ISO `YYYY-MM-DD`, including MCX display dates such as `26 Oct 2026` and compact expiry dates such as `05NOV2026`.
5. AURORA's existing validation, normalization, and deduplication remain in charge of database ingestion. The workflow logs the API result.

The source file must include Date, Symbol (or a usable contract field), Expiry Date, and Close/LTP. A single file may contain only one or some of the four symbols; the importer reports which symbols it found and does **not** fabricate missing contracts. Opportunity Radar will only have observations for contracts actually present in the imported data.

This is **daily end-of-day ingestion**, not an intraday/live feed. The actual data timestamp must remain visible in AURORA.

## Enable only after source permissions and endpoint are confirmed

In GitHub repository settings, configure:

- Repository variable `ENABLE_MCX_BHAVCOPY_AUTOMATION=true` to allow the job to run.
- Repository variable `AURORA_BHAVCOPY_AUTOMATION_CONFIRMED=true` as an operator acknowledgement that permission has been confirmed.
- Repository secret `MCX_BHAVCOPY_CSV_URL`: direct official MCX-hosted CSV or HTML-table export URL. Do not use a Market Watch endpoint or a URL whose automated access has not been authorized.
- Repository secret `AURORA_API_BASE_URL`: deployed AURORA base URL, e.g. `https://your-service.onrender.com`.
- Repository secret `AURORA_INGESTION_TOKEN`: bearer token only if the deployment's ingestion endpoint is configured to require/validate it.

The workflow is skipped unless `ENABLE_MCX_BHAVCOPY_AUTOMATION` is exactly `true`. The script also exits safely unless `AURORA_BHAVCOPY_AUTOMATION_CONFIRMED` is exactly `true`.

## Manual smoke test

Run `python backend/scripts/import_mcx_bhavcopy.py` against a local/staging AURORA instance and a permitted sample file first. Do not enable the scheduled workflow until the exact official source URL, automated-access permissions, data rights, authentication, and API response have been verified.

## Later intraday provider

Keep intraday quotes as a separate provider adapter backed by an authorized/licensed API. Do not label daily bhavcopy as live data, and do not enable the unverified public Market Watch provider to make the dashboard appear live.
