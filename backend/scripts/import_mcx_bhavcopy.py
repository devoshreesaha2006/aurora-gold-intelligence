#!/usr/bin/env python3
"""Download a permitted MCX daily CSV and send it through AURORA's existing importer.

This intentionally does not guess a download URL. Configure MCX_BHAVCOPY_CSV_URL only
for an official source and after confirming that automated access/storage is permitted.
"""
from __future__ import annotations

import csv
import io
import os
import sys
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen

MAX_BYTES = 20 * 1024 * 1024
ALLOWED_HOSTS = {"www.mcxindia.com", "mcxindia.com"}
TARGET_SYMBOLS = {"GOLDM", "GOLDTEN", "GOLDGUINEA", "GOLDPETAL"}


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def download_csv(url: str) -> bytes:
    parsed = urlparse(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
        raise RuntimeError("Bhavcopy URL must be HTTPS on an official MCX website host.")
    request = Request(url, headers={"User-Agent": "AURORA-Bhavcopy-Importer/1.0", "Accept": "text/csv,application/csv,text/plain"})
    with urlopen(request, timeout=30) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        body = response.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise RuntimeError(f"Downloaded file exceeds {MAX_BYTES} bytes.")
    if not body:
        raise RuntimeError("Downloaded file is empty.")
    if "html" in content_type or body.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        raise RuntimeError("Source returned HTML instead of a CSV file.")
    try:
        text = body.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = body.decode("latin-1")
    try:
        reader = csv.DictReader(io.StringIO(text))
        headers = [h.strip() for h in (reader.fieldnames or [])]
        if not headers:
            raise RuntimeError("CSV header row is missing.")
        rows = list(reader)
    except csv.Error as exc:
        raise RuntimeError(f"CSV parsing failed: {exc}") from exc
    if not rows:
        raise RuntimeError("CSV contains no data rows.")
    normalized_headers = {h.lower().replace(" ", "").replace("_", "") for h in headers}
    if not ({"symbol", "productcode", "instrumentname"} & normalized_headers):
        raise RuntimeError("CSV does not contain a recognized contract/symbol column.")
    symbol_col = next(h for h in headers if h.lower().replace(" ", "").replace("_", "") in {"symbol", "productcode", "instrumentname"})
    symbols = {str(row.get(symbol_col, "")).strip().upper() for row in rows}
    if not symbols.intersection(TARGET_SYMBOLS):
        raise RuntimeError("CSV has no GOLDM/GOLDTEN/GOLDGUINEA/GOLDPETAL rows; refusing to ingest.")
    return body


def upload_csv(base_url: str, token: str, content: bytes, filename: str) -> bytes:
    boundary = "----AuroraBhavcopyBoundary7MA4YWxkTrZu0gW"
    fields = {
        "data_source": "mcx_bhavcopy_official_csv",
        "is_synthetic": "false",
        "allow_duplicates": "false",
    }
    chunks = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}\r\n".encode())
    safe_filename = filename.replace('"', "")
    chunks.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{safe_filename}\"\r\nContent-Type: text/csv\r\n\r\n".encode()
        + content + b"\r\n"
    )
    chunks.append(f"--{boundary}--\r\n".encode())
    request = Request(
        base_url.rstrip("/") + "/api/data/upload",
        data=b"".join(chunks),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with urlopen(request, timeout=60) as response:
        result = response.read(2 * 1024 * 1024)
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"AURORA importer returned HTTP {response.status}: {result[:500]!r}")
        return result


def main() -> int:
    if os.environ.get("AURORA_BHAVCOPY_AUTOMATION_CONFIRMED", "").lower() != "true":
        print("Skipped safely: set AURORA_BHAVCOPY_AUTOMATION_CONFIRMED=true only after confirming source permissions.")
        return 0
    url = required_env("MCX_BHAVCOPY_CSV_URL")
    base_url = required_env("AURORA_API_BASE_URL")
    token = required_env("AURORA_INGESTION_TOKEN")
    if urlparse(base_url).scheme != "https":
        raise RuntimeError("AURORA_API_BASE_URL must use HTTPS.")
    content = download_csv(url)
    filename = urlparse(url).path.rsplit("/", 1)[-1] or f"mcx-bhavcopy-{time.strftime('%Y%m%d')}.csv"
    result = upload_csv(base_url, token, content, filename)
    print(result.decode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Bhavcopy ingestion failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
