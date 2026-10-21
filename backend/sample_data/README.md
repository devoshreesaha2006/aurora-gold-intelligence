# AURORA Market Data Ingestion Specification

> **NOTICE**: The sample CSV files in this directory contain **synthetic demo data strictly designed for validation and testing**. They are not claimed to be official live or historical MCX exchange publications.

## Supported CSV Format

The CSV ingestion pipeline (`POST /api/data/upload`) accepts standard MCX Bhavcopy exports and normalized commodity observation tables.

### Column Specification

| Column | Type | Required | Description | Example |
| :--- | :--- | :--- | :--- | :--- |
| `symbol` | String | **Yes** | Authorized gold futures contract (`GOLDM`, `GOLDTEN`, `GOLDGUINEA`, `GOLDPETAL`) | `GOLDM` |
| `trade_date` | Date | **Yes** | Trade or settlement date (`YYYY-MM-DD`, `DD/MM/YYYY`, `DD-MM-YYYY`) | `2026-10-15` |
| `expiry_date`| Date | **Yes** | Contract expiration date (`YYYY-MM-DD`, `DD/MM/YYYY`, or MCX compact `30OCT2026`) | `2026-10-30` |
| `close` | Float | **Yes** | Settlement / closing price in contract quotation currency (INR) | `62980` |
| `open` | Float | No | Session opening price (must be positive) | `62790` |
| `high` | Float | No | Session high price (must be >= low) | `63100` |
| `low` | Float | No | Session low price (must be <= high) | `62710` |
| `volume` | Integer | No | Traded lots during session (default: 0) | `15400` |
| `open_interest` | Integer | No | Outstanding contracts at session end (default: 0) | `37800` |
| `purity` | Integer/Float | No | Optional purity override (e.g. 995, 999). Defaults to contract spec | `995` |

### Validation Rules

1. **Symbol Verification**: Must match an active MCX gold contract specification.
2. **Date Ordering**: `expiry_date` cannot be earlier than `trade_date`.
3. **Numeric Sanity**: Prices must be strictly positive (`> 0`). High must be `>=` Low.
4. **Volume & OI**: Must be non-negative integers (`>= 0`).
5. **Deduplication**:
   - File level: SHA-256 checksum detects duplicate file submissions.
   - Row level: Composite constraint on `(symbol, trade_date, expiry_date)` prevents duplicate records.

### Normalization Logic

Raw contract quotes cannot be directly compared due to differing contract mechanics:
- `GOLDM`: Quoted per 10 grams, 995 purity
- `GOLDTEN`: Quoted per 10 grams, 999 purity
- `GOLDGUINEA`: Quoted per 8 grams, 999 purity
- `GOLDPETAL`: Quoted per 1 gram, 999 purity

AURORA standardizes every valid observation into:
1. `normalized_price_per_gram`: `(Quoted Price / Quoted Grams) / (Purity / 1000)`
2. `normalized_price_10g_basis`: `normalized_price_per_gram * 10 * 0.995`
