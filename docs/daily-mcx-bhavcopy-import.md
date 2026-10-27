# Daily MCX Bhavcopy Import (gated)

This adapter is deliberately **disabled by default**. It does not guess an MCX download URL and does not scrape the Market Watch page. Configure it only after MCX confirms that the selected source may be accessed automatically and that the intended storage/analytics/display use is permitted.

## Flow

1. A scheduled GitHub Actions workflow runs on weekdays at 18:00 IST.
2. It downloads a direct HTTPS CSV URL hosted on `mcxindia.com` or `www.mcxindia.com`.
3. It rejects HTML, empty/oversized files, malformed CSV, and files without GOLDM/GOLDTEN/GOLDGUINEA/GOLDPETAL rows.
4. It submits the CSV to the existing `POST /api/data/upload` endpoint with `data_source=mcx_bhavcopy_official_csv`, preserving AURORA's current validation, normalization, and deduplication.
5. It logs the API result in the workflow output.

This is **daily end-of-day ingestion**, not an intraday/live feed. The actual data timestamp must remain visible in AURORA.

## Enable only after permissions and endpoint are confirmed

In GitHub repository settings, configure:

- Repository variable `ENABLE_MCX_BHAVCOPY_AUTOMATION=true` to allow the job to run.
- Repository variable `AURORA_BHAVCOPY_AUTOMATION_CONFIRMED=true` as an operator acknowledgement that permission has been confirmed.
- Repository secret `MCX_BHAVCOPY_CSV_URL`: direct official MCX-hosted CSV URL. Do not use a Market Watch endpoint or a URL whose automated access has not been authorized.
- Repository secret `AURORA_API_BASE_URL`: deployed AURORA base URL, e.g. `https://your-service.onrender.com`.
- Repository secret `AURORA_INGESTION_TOKEN`: bearer token only if the deployment's ingestion endpoint is configured to require/validate it. If AURORA uses a different auth mechanism, adapt the upload request to that mechanism before enabling.

The workflow is skipped unless `ENABLE_MCX_BHAVCOPY_AUTOMATION` is exactly `true`. The script also exits safely unless `AURORA_BHAVCOPY_AUTOMATION_CONFIRMED` is exactly `true`.

## Manual smoke test

From the repository root, set the four environment variables above and run:

```bash
python backend/scripts/import_mcx_bhavcopy.py
```

First test against a local/staging AURORA instance and a permitted sample CSV. Do not enable the scheduled workflow until the exact official CSV URL, authentication mechanism, data rights, and importer response have been verified.

## Later intraday provider

Keep intraday quotes as a separate provider adapter backed by an authorized/licensed API. Do not label daily bhavcopy as live data, and do not enable the unverified public Market Watch provider to make the dashboard appear live.
