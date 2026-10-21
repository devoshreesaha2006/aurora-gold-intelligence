# AURORA — Commodity Intelligence & Relative-Value Platform
### Phase 2: Relative-Value Intelligence Engine (MCX Gold)

AURORA transforms Multi Commodity Exchange of India (MCX) gold commodity futures settlement data into an explainable relative-value market intelligence product. It standardizes physically distinct contracts (**GOLDM**, **GOLDTEN**, **GOLDGUINEA**, **GOLDPETAL**) to a common fine-gold basis, calculates pairwise normalized spreads across all six contract combinations, detects statistically unusual relative pricing (rolling Z-scores & empirical percentiles), audits liquidity, expiry friction, and transaction hurdles, and provides complete audit evidence trails for decision support.

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
│   └── tests/                                    # Pytest test suite (20 test cases)
│       ├── conftest.py
│       ├── test_health.py
│       ├── test_contracts.py
│       ├── test_ingestion.py
│       ├── test_market.py
│       └── test_analytics.py
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
│   ├── aurora-pipeline.js           # Phase 1 Live integration & CSV Ingest Modal
│   ├── dashboard.html               # Executive Dashboard
│   ├── contract-explorer.html       # Contract Specifications Explorer
│   ├── opportunity-radar.html       # Relative-Value Radar
│   ├── market-detective.html        # Anomaly Investigation Dossier
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
Open PowerShell in the project directory (`c:\Users\ASUS\OneDrive\Desktop\hacknHills`):

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
Verify all 20 unit, analytics, and integration tests:

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

## Testing & Verification Results

All **20 unit, quantitative, and integration tests** in `backend/tests/` passed:

```
backend/tests/test_analytics.py::test_parse_pair PASSED                  [  5%]
backend/tests/test_analytics.py::test_cost_hurdle_calculation PASSED     [ 10%]
backend/tests/test_analytics.py::test_classification_logic_all_states PASSED [ 15%]
backend/tests/test_analytics.py::test_edge_cases_zero_variance_and_insufficient_history PASSED [ 20%]
backend/tests/test_analytics.py::test_api_spreads_endpoint PASSED        [ 25%]
backend/tests/test_analytics.py::test_api_radar_endpoint PASSED          [ 30%]
backend/tests/test_analytics.py::test_api_events_endpoint PASSED         [ 35%]
backend/tests/test_analytics.py::test_api_distribution_endpoint PASSED   [ 40%]
backend/tests/test_analytics.py::test_asymmetric_dates_and_zero_future_leakage PASSED [ 45%]
backend/tests/test_analytics.py::test_api_events_filtering_by_status_and_pair PASSED [ 50%]
backend/tests/test_contracts.py::test_list_contracts PASSED              [ 55%]
backend/tests/test_contracts.py::test_contract_normalization_logic PASSED [ 60%]
backend/tests/test_health.py::test_health_check PASSED                   [ 65%]
backend/tests/test_health.py::test_market_status PASSED                  [ 70%]
backend/tests/test_ingestion.py::test_valid_csv_upload PASSED            [ 75%]
backend/tests/test_ingestion.py::test_duplicate_csv_prevention PASSED    [ 80%]
backend/tests/test_ingestion.py::test_invalid_csv_validation_report PASSED [ 85%]
backend/tests/test_ingestion.py::test_list_data_imports PASSED           [ 90%]
backend/tests/test_ingestion.py::test_database_persistence_and_relationships PASSED [ 95%]
backend/tests/test_market.py::test_market_prices_query_and_pagination PASSED [100%]

======================== 20 passed in 0.65s ========================
```

---

## Git Branches & Safety Backups

- `backup-phase0-baseline`: Preserved snapshot of original repository state before Phase 1 implementation.
- `feature/phase1-backend-pipeline`: Working branch with the complete Phase 1 implementation.
- `backup_frontend_baseline/`: Local directory backup of original frontend assets.
