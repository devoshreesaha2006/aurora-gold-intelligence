"""Public macro observations proxied server-side to avoid browser CORS restrictions.

Values are sourced directly from FRED CSV. No cached or synthetic observations are returned.
"""
import csv
import io
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/research", tags=["Research, Forecasting & Risk"])

SERIES = [
    {"id": "DGS10", "name": "US 10-year Treasury yield", "unit": "% per year", "meaning": "Nominal long-term yield"},
    {"id": "DFII10", "name": "US 10-year real yield", "unit": "% per year", "meaning": "Inflation-indexed Treasury yield"},
    {"id": "DTWEXBGS", "name": "US broad trade-weighted dollar index", "unit": "index points", "meaning": "Broad USD strength proxy"},
]


def _fetch_series(item):
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + item["id"]
    request = urllib.request.Request(url, headers={"Accept": "text/csv", "User-Agent": "AURORA-Research/1.0"})
    with urllib.request.urlopen(request, timeout=4) as response:
        content = response.read().decode("utf-8-sig")
    rows = csv.DictReader(io.StringIO(content))
    observations = []
    for row in rows:
        observed_date = (row.get("observation_date") or row.get("DATE") or row.get("date") or "").strip()
        raw_value = (row.get(item["id"]) or row.get("value") or "").strip()
        if not observed_date or not raw_value or raw_value == ".":
            continue
        try:
            numeric = float(raw_value)
            parsed_date = date.fromisoformat(observed_date)
        except (ValueError, TypeError):
            continue
        observations.append((parsed_date, numeric))
    if not observations:
        raise ValueError("FRED returned no usable observations for " + item["id"])
    observed_date, value = max(observations, key=lambda pair: pair[0])
    return {
        **item,
        "date": observed_date.isoformat(),
        "value": value,
        "age_days": max(0, (date.today() - observed_date).days),
        "source_url": "https://fred.stlouisfed.org/series/" + item["id"],
    }


@router.get("/macro")
def public_macro_observations():
    """Return the latest available FRED observations through the backend."""
    data = []
    errors = []
    with ThreadPoolExecutor(max_workers=len(SERIES)) as pool:
        futures = {pool.submit(_fetch_series, item): item for item in SERIES}
        for future in as_completed(futures):
            item = futures[future]
            try:
                data.append(future.result())
            except (urllib.error.URLError, TimeoutError, OSError, UnicodeError, ValueError) as exc:
                errors.append({"id": item["id"], "message": str(exc) or exc.__class__.__name__})
    data.sort(key=lambda item: next(i for i, source in enumerate(SERIES) if source["id"] == item["id"]))
    if not data:
        detail = "; ".join(item["id"] + ": " + item["message"] for item in errors)
        raise HTTPException(status_code=502, detail="FRED macro feed unavailable from backend. " + detail)
    return {"success": True, "provider": "FRED public CSV", "data": data, "partial": bool(errors), "errors": errors}
