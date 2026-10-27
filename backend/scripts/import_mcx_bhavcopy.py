#!/usr/bin/env python3
"""Download a permitted MCX daily bhavcopy (CSV or HTML-table .xls export),
convert it to AURORA's canonical CSV schema, and use the existing upload API.

The source URL must be explicitly configured and permitted. This script does not
scrape the Market Watch page or guess a download URL.
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import time
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MAX_BYTES = 20 * 1024 * 1024
ALLOWED_HOSTS = {"www.mcxindia.com", "mcxindia.com"}
TARGET_SYMBOLS = {"GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"}
CANONICAL_HEADERS = ["date", "symbol", "expiry_date", "open", "high", "low", "close", "volume", "open_interest"]


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def normalize_source_date(value: str, field_name: str) -> str:
    """Convert common MCX display/compact dates to ISO dates for the API importer."""
    raw = value.strip()
    if not raw:
        return raw
    for fmt in (
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%d%b%Y",
        "%d-%b-%Y",
        "%d/%b/%Y",
    ):
        try:
            from datetime import datetime
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    raise RuntimeError(f"Unsupported {field_name} date format in MCX row: {raw!r}")


def normalize_header(value: str) -> str:
    return "".join(ch.lower() for ch in value.strip() if ch.isalnum())


class TableParser(HTMLParser):
    """Extract HTML table rows, including MCX .xls files that are HTML documents."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._cell: list[str] = []
        self._row: list[str] = []
        self._table: list[list[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "table":
            self._in_table = True
            self._table = []
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._row = []
        elif self._in_table and self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if self._in_cell and tag in {"td", "th"}:
            self._row.append(" ".join("".join(self._cell).split()).strip())
            self._cell = []
            self._in_cell = False
        elif self._in_row and tag == "tr":
            if self._row:
                self._table.append(self._row)
            self._row = []
            self._in_row = False
        elif self._in_table and tag == "table":
            if self._table:
                self.tables.append(self._table)
            self._table = []
            self._in_table = False


def canonicalize_rows(rows: list[list[str]]) -> tuple[bytes, set[str]]:
    aliases = {
        "date": {"date", "tradedate", "sessiondate"},
        "symbol": {"symbol", "productcode", "contract", "contractname"},
        "instrument": {"instrument", "instrumentname"},
        "expiry_date": {"expirydate", "expiry", "expdate"},
        "open": {"open", "openprice"},
        "high": {"high", "highprice"},
        "low": {"low", "lowprice"},
        "close": {"close", "closeprice", "settleprice", "settlementprice", "ltp"},
        "volume": {"volume", "vollots", "volumelots", "tradedqty", "totalvolume", "contractstraded"},
        "open_interest": {"openinterest", "openinterestlots", "oilots", "oi"},
    }
    header_index = None
    mapping: dict[str, int] = {}
    for idx, row in enumerate(rows):
        normalized = [normalize_header(cell) for cell in row]
        candidate: dict[str, int] = {}
        for key, names in aliases.items():
            for col_idx, header in enumerate(normalized):
                if header in names:
                    candidate[key] = col_idx
                    break
        if {"date", "expiry_date", "close"}.issubset(candidate) and ("symbol" in candidate or "instrument" in candidate):
            if "symbol" not in candidate and "instrument" in candidate:
                candidate["symbol"] = candidate["instrument"]
            header_index, mapping = idx, candidate
            break
    if header_index is None:
        raise RuntimeError("Could not find a table header with Date, Symbol/Instrument, Expiry Date and Close/LTP.")

    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(CANONICAL_HEADERS)
    found_symbols: set[str] = set()
    for row in rows[header_index + 1:]:
        if len(row) <= max(mapping.values()):
            continue
        symbol = row[mapping["symbol"]].strip().upper()
        if symbol not in TARGET_SYMBOLS:
            continue
        record = []
        for key in CANONICAL_HEADERS:
            col_idx = mapping.get(key)
            value = row[col_idx].strip() if col_idx is not None and col_idx < len(row) else ""
            if key in {"date", "expiry_date"} and value:
                value = normalize_source_date(value, key)
            record.append(value)
        writer.writerow(record)
        found_symbols.add(symbol)
    if not found_symbols:
        raise RuntimeError("The downloaded file contains no GOLDM/GOLDTEN/GOLDGUINEA/GOLDPETAL rows.")
    return output.getvalue().encode("utf-8"), found_symbols



def canonicalize_json_records(records: list[dict]) -> tuple[bytes, set[str]]:
    """Convert the public MCX Bhavcopy page's JSON record array to canonical CSV."""
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(CANONICAL_HEADERS)
    found_symbols: set[str] = set()
    for item in records:
        if not isinstance(item, dict):
            continue
        normalized = {normalize_header(str(k)): v for k, v in item.items()}
        symbol = str(normalized.get("symbol") or normalized.get("productcode") or "").strip().upper()
        if symbol not in TARGET_SYMBOLS:
            continue
        date_value = normalized.get("date") or normalized.get("datedisplay") or ""
        expiry_value = normalized.get("expirydate") or normalized.get("expiry") or ""
        close_value = normalized.get("close")
        if close_value in (None, ""):
            close_value = normalized.get("ltp")
        if not date_value or not expiry_value or close_value in (None, ""):
            continue
        date_text = normalize_source_date(str(date_value), "date")
        expiry_text = normalize_source_date(str(expiry_value), "expiry_date")
        def val(*keys: str) -> str:
            for key in keys:
                value = normalized.get(key)
                if value not in (None, ""):
                    return str(value).strip()
            return ""
        writer.writerow([
            date_text, symbol, expiry_text,
            val("open"), val("high"), val("low"),
            str(close_value).strip(), val("volume", "vollots", "volumelots"),
            val("openinterest", "openinterestlots", "oi"),
        ])
        found_symbols.add(symbol)
    if not found_symbols:
        raise RuntimeError("The JSON response contains no usable GOLDM/GOLDTEN/GOLDGUINEA/GOLDPETAL rows.")
    return output.getvalue().encode("utf-8"), found_symbols


def find_json_records(text: str) -> list[dict] | None:
    """Find a JSON array in a raw JSON response or an HTML page body."""
    decoder = json.JSONDecoder()
    candidates = [0]
    candidates.extend(i for i, ch in enumerate(text) if ch == "[")
    for start in candidates:
        try:
            value, _ = decoder.raw_decode(text[start:].lstrip())
        except json.JSONDecodeError:
            continue
        if isinstance(value, list) and value and any(isinstance(row, dict) for row in value):
            return value
    return None

def download_and_convert(url: str) -> tuple[bytes, set[str], str]:
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
        raise RuntimeError("Bhavcopy URL must be HTTPS on an official MCX website host.")
    request = Request(url, headers={
        "User-Agent": "AURORA-Bhavcopy-Importer/1.1",
        "Accept": "text/csv,application/csv,text/plain,application/vnd.ms-excel,*/*",
    })
    with urlopen(request, timeout=30) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise RuntimeError(f"Downloaded file exceeds {MAX_BYTES} bytes.")
    if not body:
        raise RuntimeError("Downloaded file is empty.")
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = body.decode("latin-1")
    # The official Bhavcopy page can return its rendered records as a JSON
    # array wrapped in HTML rather than as a direct CSV download.
    records = find_json_records(text)
    if records is not None:
        try:
            converted, symbols = canonicalize_json_records(records)
            return converted, symbols, "json-records"
        except RuntimeError:
            # Continue to table parsing in case the page also contains a valid
            # downloadable table alongside unrelated JSON.
            pass
    if body.lstrip().lower().startswith((b"<!doctype html", b"<html", b"<head")) or "html" in content_type:
        parser = TableParser()
        parser.feed(text)
        for table in sorted(parser.tables, key=len, reverse=True):
            try:
                converted, symbols = canonicalize_rows(table)
                return converted, symbols, "html-table"
            except RuntimeError:
                continue
        raise RuntimeError("The response is HTML, but no supported MCX bhavcopy JSON records or table were found (login/error pages are not data).")
    converted, symbols = canonicalize_rows(list(csv.reader(io.StringIO(text))))
    return converted, symbols, "csv"


def upload_csv(base_url: str, token: str, content: bytes, filename: str) -> bytes:
    boundary = "----AuroraBhavcopyBoundary7MA4YWxkTrZu0gW"
    fields = {"data_source": "mcx_bhavcopy_official_csv", "is_synthetic": "false", "allow_duplicates": "false"}
    chunks = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    chunks.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: text/csv\r\n\r\n".encode()
        + content + b"\r\n"
    )
    chunks.append(f"--{boundary}--\r\n".encode())
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(base_url.rstrip("/") + "/api/data/upload", data=b"".join(chunks), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=60) as response:
            result = response.read(2 * 1024 * 1024)
            if response.status < 200 or response.status >= 300:
                raise RuntimeError(f"AURORA importer returned HTTP {response.status}: {result[:500]!r}")
            return result
    except HTTPError as exc:
        detail = exc.read(2000).decode("utf-8", errors="replace")
        raise RuntimeError(f"AURORA importer returned HTTP {exc.code}: {detail}") from exc


def main() -> int:
    dry_run = os.environ.get("AURORA_BHAVCOPY_DRY_RUN", "false").lower() == "true"
    url = required_env("MCX_BHAVCOPY_CSV_URL")
    base_url = required_env("AURORA_API_BASE_URL")
    token = os.environ.get("AURORA_INGESTION_TOKEN", "").strip()
    if urlparse(base_url).scheme != "https":
        raise RuntimeError("AURORA_API_BASE_URL must use HTTPS.")
    content, symbols, source_format = download_and_convert(url)
    source_name = urlparse(url).path.rsplit("/", 1)[-1]
    filename = f"mcx-bhavcopy-{time.strftime('%Y%m%d')}.csv"
    row_count = sum(1 for _ in csv.reader(io.StringIO(content.decode("utf-8")))) - 1
    print(f"Parsed MCX source format={source_format}; symbols={','.join(sorted(symbols))}; rows={row_count}.")
    if source_name:
        print(f"Source filename: {source_name}")
    if dry_run:
        print("DRY RUN complete: source parsed successfully; no upload was made to AURORA.")
        return 0
    if os.environ.get("AURORA_BHAVCOPY_AUTOMATION_CONFIRMED", "").lower() != "true":
        raise RuntimeError("Upload blocked: set repository variable AURORA_BHAVCOPY_AUTOMATION_CONFIRMED=true only after confirming MCX automated-access and data-use permissions.")
    result = upload_csv(base_url, token, content, filename)
    print(result.decode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Bhavcopy ingestion failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
