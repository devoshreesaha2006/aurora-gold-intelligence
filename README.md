# AURORA — Commodity Intelligence & Relative-Value Platform
### Phase 2: Relative-Value Intelligence Engine (MCX Gold)

AURORA transforms Multi Commodity Exchange of India (MCX) gold commodity futures settlement data into an explainable relative-value market intelligence product. It standardizes physically distinct contracts (**GOLDM**, **GOLDTEN**, **GOLDGUINEA**, **GOLDPETAL**) to a common fine-gold basis, calculates pairwise normalized spreads across all six contract combinations, detects statistically unusual relative pricing (rolling Z-scores & empirical percentiles), audits liquidity, expiry friction, and transaction hurdles, and provides complete audit evidence trails for decision support.

---

## Data Integrity & Evaluation Notes

- Treat imported Bhavcopy/CSV records as **user-imported historical data** unless the API explicitly confirms an authenticated, authorized provider feed. A file name or user-supplied source label is not proof of exchange provenance.
- Do not interpret a historical snapshot, heuristic opportunity/ranking score, spread percentile, or backtest result as a probability of profit or a live execution recommendation.
- A pair must remain **No Signal / unavailable** when required synchronized observations, expiry matching, observed liquidity, provenance, or other configured eligibility checks are missing. Missing inputs must not be treated as passing checks.
- Normalized spreads use the documented **₹ per 10g, 995 fine-gold benchmark**. Individual contract purities remain contract-specific inputs to normalization; the benchmark label does not mean every contract is 995 purity.
- Before production use, independently verify effective-dated contract specifications, source permissions, source-data quality, transaction-cost assumptions, and the behavior of the authorized provider integration. Do not claim a live feed unless the backend status confirms an authenticated and fresh provider response.

---

## Architecture Overview (Phase 1 & Phase 2)

```
hacknHills/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entrypoint, CORS, lifespan seeding
│   │   ├── config.py                # Pydantic BaseSettings, environment configuration
│   │   ├── database.py              # SQLAlchemy engine, session maker, get_db dependency
│   │   ├── models/                  # SQLAlchemy ORM entities
│   │   │   ├── contract.py          # MCX Gold contract specifications & physical parameters
│   │   │   ├── market_observation.py# Raw market metrics & normalized fine-gold price records
│   │   │   └── data_import.py       # Ingestion audit log (batches, checksums, error counts)
│   │   ├── schemas/                 # Pydantic request/response schemas
│   │   │   ├── common.py            # StandardResponse envelope, ErrorDetail, PaginationMeta
│   │   │   ├── contract.py          # Contract schemas
│   │   │   ├── market.py            # MarketStatusRead, MarketPriceItem, MarketPriceList
│   │   │   ├── ingestion.py         # UploadResult, RowError, ImportBatchRead
│   │   │   └── analytics.py         # PairSpreadPoint, RadarResponse, EventsResponse, DistributionResponse
│   │   ├── services/
│   │   │   ├── normalization.py     # Common ₹/g fine-gold & 10g 995 basis conversion engine
│   │   │   ├── contract_service.py  # Contract querying and startup specification seeder
│   │   │   ├── ingestion_service.py # CSV parser, date normalizer, validator & deduplicator
│   │   │   └── analytics_service.py # Pairwise spread engine, rolling Z-score, trap classifier & distribution
│   │   ├── providers/
│   │   │   ├── base.py              # Abstract MarketDataProvider interface
│   │   │   ├── static_provider.py   # Local SQLite database & staged CSV provider
│   │   │   └── live_mock.py         # Authorized live feed adapter (demands valid exchange keys)
│   │   └── api/
│   │       ├── health.py            # GET /api/health
│   │       ├── market.py            # GET /api/market/status, GET /api/market/prices
│   │       ├── contracts.py         # GET /api/contracts
│   │       ├── ingestion.py         # POST /api/data/upload, GET /api/data/imports
│   │       ├── analytics.py         # GET /api/analytics/{spreads,radar,events,distribution}
│   │       └── router.py            # Root API router (/api)
│   ├── sample_data/
│   │   ├── sample_mcx_gold_bhavcopy_valid.csv    # 16-row valid synthetic test dataset
│   │   ├── sample_mcx_gold_bhavcopy_invalid.csv  # 8-row malformed CSV testing diagnostics
│   │   └── README.md                             # CSV schema and validation documentation
│   └── tests/                                    # Pytest regression suite
│       ├── conftest.py
│       ├── test_health.py
│       ├── test_contracts.py
│       ├── test_ingestion.py
│       ├── test_market.py
│       ├── test_analytics.py
│       ├── test_backtests.py
│       ├── test_backtest_spread_history.py
│       ├── test_frontend_data_safety.py
│       ├── test_authorized_provider.py
│       ├── test_provider_provenance.py
│       ├── test_config_database_path.py
│       └── test_observation_metadata_migration.py
├── AURORA-website (1)/AURORA/       # Preserved Frontend with 3D/Claymorphism/Glassmorphism
│   ├── aurora-pipeline.js           # Phase 1 Live integration & Phase 2 Analytics Sync
│   ├── dashboard.html               # Executive Dashboard
│   ├── contract-explorer.html       # Contract Specifications Explorer
│   ├── opportunity-radar.html       # Relative-Value Radar (Live 6-Pair Radar & Bell Curve)
│   ├── market-detective.html        # Anomaly Investigation Dossier (Live Event Dossier)
│   └── backtesting-lab.html         # Walk-Forward Backtester
├── .env.example                     # Environment template
├── requirements.txt                 # Python dependencies
└── README.md
```

---

## Quickstart Guide (Windows PowerShell)

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.13)
- Windows PowerShell

### 2. Set Up Virtual Environment & Dependencies
Open PowerShell in the repository root (the folder containing `README.md`, `requirements.txt`, and `backend/`).

```powershell
# Create Python virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Default `.env` configuration uses zero-config SQLite (`sqlite:///./aurora.db`) and demo mode.

### 4. Run Verification Tests
Run the complete backend regression, analytics, and integration test suite:

```powershell
python -m pytest backend/tests -v
```

### 5. Start the AURORA FastAPI Backend
Launch the backend server:

```powershell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

The database tables are automatically initialized and default MCX Gold contracts (**GOLDM**, **GOLDTEN**, **GOLDGUINEA**, **GOLDPETAL**) are seeded on first startup.

### 6. Serve and Open the Frontend
In a second PowerShell terminal:

```powershell
# Serve frontend via Python HTTP server
python -m http.server 3000 --directory "AURORA-website (1)\AURORA"
```

Or open directly in your default browser:
```powershell
Start-Process "AURORA-website (1)\AURORA\index.html"
```

---

## Local URLs

| Component | Local URL | Description |
| :--- | :--- | :--- |
| **Intro Page** | [http://127.0.0.1:5500/index.html](http://127.0.0.1:5500/index.html) | Interactive 3D Gold intro experience |
| **Main Landing Page** | [http://127.0.0.1:5500/landing.html](http://127.0.0.1:5500/landing.html) | Platform overview, Login, Sign Up, & Demo Login |
| **Executive Dashboard** | [http://127.0.0.1:5500/dashboard.html](http://127.0.0.1:5500/dashboard.html) | Main Dashboard with surveillance & Expiry Calendar |
| **Opportunity Radar** | [http://127.0.0.1:5500/opportunity-radar.html](http://127.0.0.1:5500/opportunity-radar.html) | Relative-Value Radar (6-pair distribution & Bell Curve) |
| **Market Detective** | [http://127.0.0.1:5500/market-detective.html](http://127.0.0.1:5500/market-detective.html) | Anomaly Investigation & Step 08 Historical Memory |
| **Backtesting Lab & Simulator** | [http://127.0.0.1:5500/backtesting-lab.html](http://127.0.0.1:5500/backtesting-lab.html) | Walk-Forward Backtester & Market Simulator |
| **Backend API Root** | [http://127.0.0.1:8000/](http://127.0.0.1:8000/) | Service root endpoint |
| **Interactive API Docs** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Interactive Swagger UI API Documentation |
| **ReDoc Documentation** | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) | Alternative OpenAPI specification documentation |
| **Health Check Endpoint**| [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health) | System health and database connectivity probe |
| **Market Status** | [http://127.0.0.1:8000/api/market/status](http://127.0.0.1:8000/api/market/status) | Real-time connection, data mode & observations count |

---

## Phase 1 API Endpoints

### 1. `GET /api/health`
Verifies backend liveness, active environment, and database connectivity.

### 2. `GET /api/market/status`
Returns real-time connectivity status. Accurately reports `data_mode`:
- `staged_csv` (when historical Bhavcopy files have been ingested)
- `demo_synthetic` (when demo observations are active)
- `live_feed_authorized` (active exchange feed)
- `live_feed_disconnected` (live provider configured but awaiting credentials)

### 3. `POST /api/data/upload`
Uploads and validates MCX Gold Bhavcopy CSV data.
- **Validation**: Verifies symbol whitelist, date coherence (`expiry_date >= trade_date`), positive prices, high >= low, and non-negative volume/OI.
- **Normalization**: Standardizes raw quotes into `normalized_price_per_gram` (fine gold) and `normalized_price_10g_basis`.
- **Deduplication**: Computes SHA-256 file hash to prevent accidental re-imports. Also enforces unique row constraint on `(symbol, trade_date, expiry_date)`.
- **Diagnostics**: Returns line-by-line error reports for rejected rows.

### 4. `GET /api/contracts`
Returns the 4 official MCX Gold contract specifications:
- **GOLDM**: 100g unit, quoted per 10g, 995 purity
- **GOLDTEN**: 10g unit, quoted per 10g, 999 purity (listed 2025)
- **GOLDGUINEA**: 8g unit, quoted per 8g, 999 purity
- **GOLDPETAL**: 1g unit, quoted per 1g, 999 purity

### 5. `GET /api/market/prices`
Queries historical observations with both raw quoted prices and computed fine-gold normalized metrics. Supports `symbol`, `start_date`, `end_date`, `limit`, and `offset`.

### 6. `GET /api/data/imports`
Returns audit history of all ingested batches with file checksums, timestamps, and accepted/rejected metrics.

---

## Phase 2 Relative-Value Intelligence Endpoints

### 7. `GET /api/analytics/spreads`
Queries time-series of pairwise normalized price spreads for any contract pair (e.g. `GOLDM-GOLDPETAL`, `GOLDTEN-GOLDGUINEA`, etc.):
- **Metrics**: Normalized spread (₹ per 10g benchmark 995 basis), rolling mean ($\mu$), unbiased sample standard deviation ($\sigma$, `ddof=1`), rolling Z-score, empirical percentile rank.
- **Controls**: Strict trailing lookback ($N \ge 2$, window default 30 days) with **zero future look-ahead bias**. Returns `insufficient_history` or `zero_variance` status where applicable.

### 8. `GET /api/analytics/radar`
Computes the 6-pair relative-value matrix on the latest synchronized market date:
- Evaluates `GOLDM-GOLDTEN`, `GOLDM-GOLDGUINEA`, `GOLDM-GOLDPETAL`, `GOLDTEN-GOLDGUINEA`, `GOLDTEN-GOLDPETAL`, and `GOLDGUINEA-GOLDPETAL`.
- Emits 0-100 `deviation_intensity`, `opportunity_score`, and `trap_risk_score`.
- Classifies each pair into `Investigate`, `Watch`, `Cost-Blocked`, `Expiry-Risk`, or `No Signal`.

### 9. `GET /api/analytics/events`
Returns detected market dislocation events with complete audit trails:
- Includes raw quoted prices, standardized basis, rolling statistical cutoffs, days to expiry ($DTE$), volume/OI liquidity proxy, estimated transaction friction hurdle, and plain-language explanation of triggered rules.

### 10. `GET /api/analytics/distribution`
Calculates empirical spread frequency distribution and theoretical Gaussian PDF overlay for the distribution chart:
- Outputs histogram bins, empirical frequencies, sample mean, sigma, median, skewness, kurtosis, and current spread position.

---

## Phase 3 Walk-Forward Backtesting Lab Endpoints

### 11. `POST /api/backtests`
Executes an audit-grade walk-forward historical simulation of statistical mean-reversion spread trading across any MCX Gold contract pair:
- **Request Parameters**:
  - `pair`: Canonical pair string (e.g. `GOLDM-GOLDPETAL`, `GOLDTEN-GOLDGUINEA`).
  - `lookback_days`: Trailing rolling estimation window (e.g. 30 days).
  - `entry_z_threshold`: Statistical entry hurdle (e.g. 1.5σ).
  - `exit_z_threshold`: Statistical mean-reversion exit target (e.g. 0.0σ or 0.5σ).
  - `stop_loss_z`: Emergency structural risk stop (e.g. 3.0σ).
  - `max_holding_days`: Time-decay exit safeguard.
  - `slippage_per_10g` & `fee_rate`: Granular transaction cost and exchange fee deductions.
- **Safety Controls**:
  - Strict point-in-time calculation with zero future data leakage.
  - Expiry roll boundary protection: rolls between successive delivery months never book cross-contract level jumps as phantom PnL.
  - Liquid-only execution: rejects positions during unobserved volume periods even when min_volume hurdle is relaxed.
- **Output Metrics**: Total cumulative PnL (₹), annualized Sharpe ratio, Maximum Drawdown (%), Win Rate (%), Total Trade Count, and complete date-by-date trade log.

---

---

## Deterministic ML & Quantitative Intelligence Audit Statement

AURORA operates on strict financial engineering and statistical principles rather than generative AI or black-box predictive models:
- **Zero Hallucination / Deterministic Analytics**: Every metric, rolling mean, sample variance, Z-score, and cost hurdle is computed via deterministic, auditable mathematical formulations. We deliberately reject uninterpretable deep neural networks or generative LLMs for pricing signals.
- **Sample Variance Rigor**: Rolling statistics enforce unbiased Bessel correction ($ddof=1$) with $N \ge 2$ observations. Where volatility collapses to zero, explicit `zero_variance` flags prevent division-by-zero anomalies.
- **Multi-Stage Funnel Diagnostics**: The system clearly segregates the mathematical spread deviation (0-100 Intensity) from the Opportunity Ranking Score and Risk Traps. An extreme deviation does **not** equal a recommendation; liquidity traps, expiry friction, and transaction cost hurdles explicitly block trade classification.
- **Provenance Separation**: Rigorous database and API filters isolate user-imported historical Bhavcopy records, synthetic demo fixtures, and authenticated live provider feeds so non-live data is never presented as an active exchange quote.

---

## Testing & Verification Results

The entire backend and frontend data integrity suite contains **108 automated tests** across 12 modules. All **108 tests pass cleanly** (100% pass rate in ~2 seconds):

| Test Module | Tests | Focus Area |
| :--- | :---: | :--- |
| `test_analytics.py` | 28 | 6-pair spread math, 995 basis normalization, rolling Z-scores, empirical distributions, transitivity, expiry synchronization |
| `test_authorized_provider.py` | 11 | MCX live feed adapter, credential authentication, timestamp verification, delayed/stale data protection |
| `test_backtests.py` | 11 | Walk-forward backtest simulation, parameter validation, cost hurdles, execution realism |
| `test_backtest_spread_history.py` | 1 | Expiry roll mechanics and cross-contract jump safety |
| `test_config_database_path.py` | 2 | Database path resolution and multi-environment configuration integrity |
| `test_contracts.py` | 6 | Contract specifications (GOLDM, GOLDTEN, GOLDGUINEA, GOLDPETAL) and physical conversion logic |
| `test_frontend_data_safety.py` | 24 | UI safety, historical freshness badges, status consistency, card coverage, anti-hallucination rendering |
| `test_health.py` | 2 | Service liveness and database connectivity |
| `test_ingestion.py` | 10 | Bhavcopy CSV parsing, SHA-256 deduplication, row-level validation, atomic batch ingestion |
| `test_market.py` | 5 | Querying market prices, pagination, exclusion of test/synthetic data from analytics |
| `test_observation_metadata_migration.py` | 1 | Schema migration safety and row persistence |
| `test_provider_provenance.py` | 7 | Strict separation of user-imported CSV, test data, synthetic data, and authenticated live feed |
| **Total Passed** | **108 / 108** | **Zero Regressions (100% Pass Rate)** |

```powershell
# Run full test suite
python -m pytest backend/tests -v
# Result: 108 passed, 2 warnings in 1.76s
```

### Static Code Analysis & Syntax Checks
- **JavaScript Syntax**: `node --check` executed across all 14 project JavaScript files with 0 errors.
- **Git Tree Cleanliness**: `git diff --check` executed with 0 trailing whitespace or patch errors.

---

## Authorized MCX Provider Adapter (Phase 2 Integration Boundary)

The backend supports an authorized MCX distributor bridge through the existing
`MarketDataProvider` factory and `GET /api/market/status`. MCX's official feed is
contracted and does not publish a generic REST quote protocol. The adapter accepts
the HTTPS response contract in `backend/app/providers/README.md`; a distributor or
their authorized integration must provide that bridge. An API key or URL alone
does not enable a connected status.

For production, request a current MCX feed quote and agreement directly from MCX
or an authorized distributor. The current MCX datafeed page describes real-time
Level 1/2, delayed snapshots, EOD Bhavcopy and historical order/trade products.
MCX says public websites may display delayed data only and data use/display is
subject to agreements. Its page currently lists internet feed connectivity at
₹1,00,000 plus taxes annually; verify the product-level and current total charges
with MCX before ordering. For private evaluation, broker APIs may return MCX
quotes, but their terms and storage/display permissions differ and are not a
substitute for AURORA-wide distribution rights.

### Windows PowerShell setup

1. Obtain a written MCX/distributor agreement that permits the intended AURORA
   audience, display, analysis, and persistence. Get the distributor's HTTPS
   bridge URL and provider-issued API key and secret. The vendor must implement
   the payload contract in `backend/app/providers/README.md` and return an explicit
   authenticated response, `MCX` exchange, feed type, expiry, and timezone-aware
   timestamps.
2. From the project root, create/update the ignored local environment file:

   ```powershell
   Copy-Item .env.example .env -ErrorAction SilentlyContinue
   notepad .env
   ```

   Set `DATA_MODE=live_feed_authorized`, the provider URL/name/credentials and
   timeout/freshness values. Set `MCX_FEED_LICENSE_CONFIRMED=true` only after the
   agreement is in force. Keep `.env` private; do not paste secrets into frontend
   files, source control, screenshots, or logs.
3. Install and run the backend:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python -m pytest backend/tests -q
   uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
   ```

   The startup migration adds nullable provider timestamp and verification columns
   to existing `market_observations` tables without deleting or rewriting rows.
4. Open `http://127.0.0.1:8000/api/market/status`. Check `feed_status`,
   `authentication_state`, `last_provider_timestamp`, `feed_freshness_seconds`,
   and `data_provenance`. It reports `LIVE` only after an authenticated response
   with validated, recent MCX quotes has been persisted. Delayed data is labelled
   `DELAYED`; old observations are `STALE`; absent or invalid data is
   `UNAVAILABLE`. The CSV import remains available at `POST /api/data/upload` and
   is labelled user-imported historical data rather than provider-verified data.

This adapter stores the latest provider observation per existing
`(symbol, trade_date, expiry_date)` key, not every intraday tick. It refuses to
replace a CSV or other non-provider row for that key. Confirm the licensed storage
scope accommodates this model; use a purpose-built tick store only if the agreed
feed and analytics require tick-level history.

---

---

## Demonstration & Presentation Walkthrough

Follow this step-by-step route to showcase the complete AURORA platform:

1. **Experience Entry (`index.html` → `landing.html`)**:
   - Start at `index.html` featuring the 3D gold experience and smooth transition to `landing.html`.
   - Click **Demo Login** or **Launch Platform** to enter the authenticated workspace directly without friction.
2. **Executive Dashboard (`dashboard.html`)**:
   - View top surveillance KPIs, contract status cards, live contract spread overview, and the Expiry Calendar.
   - Note the **Market Status badge** in the header displaying data provenance and connection health.
3. **Opportunity Radar (`opportunity-radar.html`)**:
   - Inspect the interactive 6-pair radar matrix and spread distribution bell curve.
   - Check the **Historical Data Freshness Indicator** (e.g. displaying snapshot date, calendar age, and stale warning).
   - Use pair filter buttons (`All Pairs`, `Investigate`, `Cost-Blocked`, `Expiry-Risk`) to see responsive card filtering.
4. **Market Detective (`market-detective.html`)**:
   - Examine anomaly dossiers with complete audit trails, step-by-step diagnostic breakdown, raw prices, normalized basis, and transaction hurdle checks.
5. **Contract Explorer (`contract-explorer.html`)**:
   - Explore detailed specifications for all 4 MCX Gold contracts (**GOLDM**, **GOLDTEN**, **GOLDGUINEA**, **GOLDPETAL**).
   - View the historical rolling price chart loaded with 2,000 eligible historical observations.
6. **Backtesting Lab & Simulator (`backtesting-lab.html`)**:
   - Run walk-forward backtest simulations across contract pairs with configurable rolling lookbacks and Z-score entry/exit hurdles.
   - Analyze equity curves, Sharpe ratio, max drawdown, and execution logs.
7. **Bhavcopy Ingestion Modal**:
   - Click **Import Bhavcopy** in any top navigation bar to inspect CSV upload validation, SHA-256 deduplication, and historical import audit trails.

---

## Frontend API Configuration

The dashboard, Contract Explorer, and Backtesting Lab use a configurable backend URL:

- Local development on `localhost` / `127.0.0.1`: defaults to `http://127.0.0.1:8000`.
- Same-origin deployment: defaults to the current site's `/api` endpoint.
- Separate frontend/backend deployment: define `window.AURORA_API_BASE` **before** loading the page's live JavaScript. Use the backend origin plus `/api` for the dashboard and Contract Explorer (for example, `https://api.example.com/api`); Backtesting Lab accepts the backend origin (for example, `https://api.example.com`) because its requests append `/api/...`.

Do not put provider credentials in this frontend setting. Keep them only in the backend's ignored `.env` file.

---

## Git Branches & Safety Backups

- `backup-phase0-baseline`: Preserved snapshot of original repository state before Phase 1 implementation.
- `feature/phase1-backend-pipeline`: Working branch with the complete Phase 1 implementation.
- `backup_frontend_baseline/`: Local directory backup of original frontend assets.
