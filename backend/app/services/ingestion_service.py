import csv
import io
import hashlib
import json
from datetime import datetime, date
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy.orm import Session

from backend.app.models.contract import Contract
from backend.app.models.market_observation import MarketObservation
from backend.app.models.data_import import ImportBatch
from backend.app.schemas.ingestion import UploadResult, RowError
from backend.app.services.normalization import normalize_price, MCX_GOLD_DEFAULTS
from backend.app.services.contract_service import get_all_contracts, seed_default_contracts


MONTH_MAP = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
}


def parse_flexible_date(val: Any) -> Optional[date]:
    """
    Parses various date conventions seen in MCX Bhavcopy & standard datasets:
    - 2026-10-15 (ISO)
    - 15/10/2026 (DD/MM/YYYY)
    - 15-10-2026 (DD-MM-YYYY)
    - 04SEP2026 (MCX compact)
    - 04-SEP-2026
    """
    if not val:
        return None
    val_str = str(val).strip().upper()
    if not val_str:
        return None

    # Try ISO
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(val_str, fmt).date()
        except ValueError:
            continue

    # Try compact Bhavcopy: e.g. 04SEP2026 or 4SEP2026 or 04-SEP-2026
    clean_val = val_str.replace("-", "").replace("/", "")
    if len(clean_val) in (8, 9):
        # 2 digits day, 3 chars month, 4 digits year or 1 digit day
        try:
            day_part = clean_val[:-7]
            month_part = clean_val[-7:-4]
            year_part = clean_val[-4:]
            if month_part in MONTH_MAP:
                return date(int(year_part), MONTH_MAP[month_part], int(day_part))
        except (ValueError, KeyError):
            pass

    return None


def parse_numeric(val: Any, field_name: str, allow_none: bool = True) -> Optional[float]:
    if val is None or str(val).strip() == "" or str(val).strip().lower() in ("nan", "null", "none", "-"):
        if allow_none:
            return None
        raise ValueError(f"Field '{field_name}' cannot be empty")
    try:
        clean = str(val).replace(",", "").strip()
        num = float(clean)
        return num
    except (ValueError, TypeError):
        raise ValueError(f"Field '{field_name}' must be a valid number, got '{val}'")


def compute_file_hash(content: bytes) -> str:
    """Computes SHA-256 hash of raw file bytes for deduplication."""
    return hashlib.sha256(content).hexdigest()


class CsvIngestionService:
    def __init__(self, db: Session):
        self.db = db
        # Cache contracts
        contracts = get_all_contracts(db)
        if not contracts:
            contracts = seed_default_contracts(db)
        self.contract_map: Dict[str, Contract] = {c.symbol.upper(): c for c in contracts}

    def process_csv(
        self,
        file_bytes: bytes,
        filename: str,
        data_source: str = "csv_upload",
        is_synthetic: bool = False,
        allow_duplicates: bool = False
    ) -> UploadResult:
        file_hash = compute_file_hash(file_bytes)

        # Check if identical file was already imported
        existing_batch = self.db.query(ImportBatch).filter(ImportBatch.file_hash == file_hash).first()
        if existing_batch and not allow_duplicates:
            return UploadResult(
                batch_id=existing_batch.id,
                filename=filename,
                file_hash=file_hash,
                data_source=data_source,
                is_synthetic=is_synthetic,
                total_rows=existing_batch.total_rows,
                accepted_rows=0,
                rejected_rows=0,
                duplicate_rows=existing_batch.accepted_rows,
                status="completed",
                errors=[],
                message=f"Duplicate file ignored: previously imported as Batch #{existing_batch.id} at {existing_batch.created_at.isoformat()}."
            )

        # Decode CSV content
        try:
            text = file_bytes.decode("utf-8-sig")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
            except Exception as e:
                return UploadResult(
                    batch_id=0,
                    filename=filename,
                    file_hash=file_hash,
                    data_source=data_source,
                    is_synthetic=is_synthetic,
                    total_rows=0,
                    accepted_rows=0,
                    rejected_rows=0,
                    duplicate_rows=0,
                    status="failed",
                    errors=[RowError(row_number=0, field="file", reason=f"File encoding not recognized: {str(e)}")],
                    message="Failed to decode CSV file."
                )

        reader = csv.reader(io.StringIO(text))
        rows = list(reader)

        if not rows:
            return UploadResult(
                batch_id=0,
                filename=filename,
                file_hash=file_hash,
                data_source=data_source,
                is_synthetic=is_synthetic,
                total_rows=0,
                accepted_rows=0,
                rejected_rows=0,
                duplicate_rows=0,
                status="failed",
                errors=[RowError(row_number=0, field="header", reason="CSV file is empty")],
                message="CSV file is completely empty."
            )

        raw_header = [h.strip().lower().replace(" ", "_").replace(".", "") for h in rows[0]]
        
        # Build column index mapping
        col_map = self._map_columns(raw_header)
        missing_critical = []
        for req in ("symbol", "date", "expiry_date", "close"):
            if req not in col_map:
                missing_critical.append(req)

        if missing_critical:
            return UploadResult(
                batch_id=0,
                filename=filename,
                file_hash=file_hash,
                data_source=data_source,
                is_synthetic=is_synthetic,
                total_rows=len(rows) - 1,
                accepted_rows=0,
                rejected_rows=len(rows) - 1,
                duplicate_rows=0,
                status="failed",
                errors=[RowError(
                    row_number=0,
                    field="header",
                    reason=f"Missing required columns in CSV header: {', '.join(missing_critical)}. Found headers: {raw_header}"
                )],
                message=f"Missing required columns: {', '.join(missing_critical)}."
            )

        # Create ImportBatch record
        batch = ImportBatch(
            filename=filename,
            file_hash=file_hash,
            total_rows=len(rows) - 1,
            data_source=data_source,
            is_synthetic=is_synthetic,
            error_summary=None
        )
        self.db.add(batch)
        self.db.flush()

        accepted_observations: List[MarketObservation] = []
        errors: List[RowError] = []
        duplicate_count = 0
        seen_in_batch = set()

        for idx, row in enumerate(rows[1:], start=1):
            if not row or all(c.strip() == "" for c in row):
                # Skip blank lines without counting as errors
                continue

            parsed_or_err = self._parse_row(idx, row, col_map, batch.id, data_source, is_synthetic)
            if isinstance(parsed_or_err, RowError):
                errors.append(parsed_or_err)
                continue

            obs = parsed_or_err
            # In-batch duplicate check
            batch_key = (obs.symbol, obs.trade_date, obs.expiry_date)
            if batch_key in seen_in_batch:
                duplicate_count += 1
                errors.append(RowError(
                    row_number=idx,
                    field="symbol+date+expiry",
                    reason=f"Duplicate observation within same CSV for {obs.symbol} on {obs.trade_date} expiring {obs.expiry_date}"
                ))
                continue
            seen_in_batch.add(batch_key)

            # In-database duplicate check
            existing_obs = self.db.query(MarketObservation).filter(
                MarketObservation.symbol == obs.symbol,
                MarketObservation.trade_date == obs.trade_date,
                MarketObservation.expiry_date == obs.expiry_date
            ).first()

            if existing_obs:
                duplicate_count += 1
                continue

            accepted_observations.append(obs)

        # Batch insert valid observations
        if accepted_observations:
            self.db.bulk_save_objects(accepted_observations)

        # Update batch summary
        batch.accepted_rows = len(accepted_observations)
        batch.rejected_rows = len(errors)
        batch.total_rows = len(accepted_observations) + len(errors) + duplicate_count
        if errors:
            batch.error_summary = json.dumps([e.model_dump() for e in errors[:50]], default=str)
        self.db.commit()

        status = "completed"
        if errors and not accepted_observations:
            status = "failed"
        elif errors and accepted_observations:
            status = "partial_success"

        msg = (
            f"Ingestion {status}: {len(accepted_observations)} accepted, "
            f"{len(errors)} rejected, {duplicate_count} duplicates skipped."
        )

        return UploadResult(
            batch_id=batch.id,
            filename=filename,
            file_hash=file_hash,
            data_source=data_source,
            is_synthetic=is_synthetic,
            total_rows=batch.total_rows,
            accepted_rows=len(accepted_observations),
            rejected_rows=len(errors),
            duplicate_rows=duplicate_count,
            status=status,
            errors=errors,
            message=msg
        )

    def _map_columns(self, headers: List[str]) -> Dict[str, int]:
        mapping = {}
        alias_map = {
            "symbol": ["symbol", "contract", "contract_name", "instrument"],
            "date": ["date", "trade_date", "tradedate", "session_date", "timestamp"],
            "expiry_date": ["expiry_date", "expiry", "expirydate", "exp_date"],
            "open": ["open", "open_price", "openprice"],
            "high": ["high", "high_price", "highprice"],
            "low": ["low", "low_price", "lowprice"],
            "close": ["close", "close_price", "closeprice", "settle_price", "settlement_price", "ltp"],
            "volume": ["volume", "vol", "traded_qty", "total_volume", "contracts_traded"],
            "open_interest": ["open_interest", "openinterest", "oi"],
            "purity": ["purity", "fineness"],
            "quote_unit": ["quote_unit", "quoted_per", "quote_grams"]
        }

        for std_col, aliases in alias_map.items():
            for idx, h in enumerate(headers):
                if h in aliases or any(h == a.replace("_", "") for a in aliases):
                    mapping[std_col] = idx
                    break

        return mapping

    def _parse_row(
        self,
        row_num: int,
        row: List[str],
        col_map: Dict[str, int],
        batch_id: int,
        data_source: str,
        is_synthetic: bool
    ) -> Any:
        def get_val(col_key: str) -> Optional[str]:
            if col_key in col_map and col_map[col_key] < len(row):
                v = row[col_map[col_key]].strip()
                return v if v else None
            return None

        # 1. Validate Symbol
        raw_symbol = get_val("symbol")
        if not raw_symbol:
            return RowError(row_number=row_num, field="symbol", reason="Contract symbol is missing or blank")
        symbol = raw_symbol.upper()
        if symbol not in self.contract_map and symbol not in MCX_GOLD_DEFAULTS:
            return RowError(
                row_number=row_num,
                field="symbol",
                reason=f"Unknown commodity contract '{symbol}'. Expected one of: {list(MCX_GOLD_DEFAULTS.keys())}"
            )

        contract_spec = self.contract_map.get(symbol) or MCX_GOLD_DEFAULTS[symbol]
        quote_unit_grams = getattr(contract_spec, "quote_unit_grams", None) or contract_spec["quote_unit_grams"]
        purity_factor = getattr(contract_spec, "purity_factor", None) or contract_spec["purity_factor"]

        # Override with row-level purity if provided
        raw_purity = get_val("purity")
        if raw_purity:
            try:
                p_val = float(raw_purity)
                purity_factor = p_val / 1000.0 if p_val > 1.0 else p_val
            except ValueError:
                return RowError(row_number=row_num, field="purity", reason=f"Invalid purity format '{raw_purity}'")

        # 2. Validate Trade Date
        raw_date = get_val("date")
        trade_date = parse_flexible_date(raw_date)
        if not trade_date:
            return RowError(row_number=row_num, field="date", reason=f"Invalid or unrecognizable trade date format '{raw_date}'")

        # 3. Validate Expiry Date
        raw_expiry = get_val("expiry_date")
        expiry_date = parse_flexible_date(raw_expiry)
        if not expiry_date:
            return RowError(row_number=row_num, field="expiry_date", reason=f"Invalid or unrecognizable expiry date format '{raw_expiry}'")

        if expiry_date < trade_date:
            return RowError(
                row_number=row_num,
                field="expiry_date",
                reason=f"Expiry date ({expiry_date}) cannot be earlier than trade date ({trade_date})"
            )

        # 4. Validate Prices
        try:
            close_price = parse_numeric(get_val("close"), "close", allow_none=False)
            if close_price <= 0:
                return RowError(row_number=row_num, field="close", reason=f"Close price must be positive, got {close_price}")
        except ValueError as e:
            return RowError(row_number=row_num, field="close", reason=str(e))

        try:
            open_price = parse_numeric(get_val("open"), "open", allow_none=True)
            # Some historical MCX CSVs encode an unavailable opening price as 0.
            # Preserve the observation but represent the missing open as None;
            # never treat zero as a real market price.
            if open_price == 0:
                open_price = None
            elif open_price is not None and open_price < 0:
                return RowError(row_number=row_num, field="open", reason=f"Open price cannot be negative, got {open_price}")
        except ValueError as e:
            return RowError(row_number=row_num, field="open", reason=str(e))

        try:
            high_price = parse_numeric(get_val("high"), "high", allow_none=True)
            if high_price is not None and high_price <= 0:
                return RowError(row_number=row_num, field="high", reason=f"High price must be positive, got {high_price}")
        except ValueError as e:
            return RowError(row_number=row_num, field="high", reason=str(e))

        try:
            low_price = parse_numeric(get_val("low"), "low", allow_none=True)
            if low_price is not None and low_price <= 0:
                return RowError(row_number=row_num, field="low", reason=f"Low price must be positive, got {low_price}")
        except ValueError as e:
            return RowError(row_number=row_num, field="low", reason=str(e))

        if high_price is not None and low_price is not None and high_price < low_price:
            return RowError(row_number=row_num, field="high/low", reason=f"High price ({high_price}) cannot be lower than Low price ({low_price})")

        # 5. Validate Volume & OI
        try:
            volume_observed = get_val("volume") is not None
            vol_raw = parse_numeric(get_val("volume"), "volume", allow_none=True)
            volume = int(vol_raw) if vol_raw is not None else 0
            if volume < 0:
                return RowError(row_number=row_num, field="volume", reason="Volume cannot be negative")
        except ValueError as e:
            return RowError(row_number=row_num, field="volume", reason=str(e))

        try:
            open_interest_observed = get_val("open_interest") is not None
            oi_raw = parse_numeric(get_val("open_interest"), "open_interest", allow_none=True)
            open_interest = int(oi_raw) if oi_raw is not None else 0
            if open_interest < 0:
                return RowError(row_number=row_num, field="open_interest", reason="Open interest cannot be negative")
        except ValueError as e:
            return RowError(row_number=row_num, field="open_interest", reason=str(e))

        # 6. Compute Normalization
        try:
            norm_per_gram, norm_10g_basis = normalize_price(close_price, quote_unit_grams, purity_factor)
        except Exception as e:
            return RowError(row_number=row_num, field="normalization", reason=f"Failed price normalization: {str(e)}")

        return MarketObservation(
            symbol=symbol,
            trade_date=trade_date,
            expiry_date=expiry_date,
            open_price=open_price,
            high_price=high_price,
            low_price=low_price,
            close_price=close_price,
            volume=volume,
            open_interest=open_interest,
            volume_observed=volume_observed,
            open_interest_observed=open_interest_observed,
            normalized_price_per_gram=norm_per_gram,
            normalized_price_10g_basis=norm_10g_basis,
            data_source=data_source,
            is_synthetic=is_synthetic,
            import_batch_id=batch_id
        )
