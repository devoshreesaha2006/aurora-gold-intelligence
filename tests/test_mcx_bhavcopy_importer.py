import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "backend" / "scripts" / "import_mcx_bhavcopy.py"
SPEC = importlib.util.spec_from_file_location("import_mcx_bhavcopy", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_html_table_xls_is_converted_to_canonical_csv():
    html = """
    <html><body><table>
      <tr><th>Date</th><th>Instrument Name</th><th>Symbol</th><th>Expiry Date</th>
      <th>Open</th><th>High</th><th>Low</th><th>Close</th><th>Volume(Lots)</th><th>Open Interest(Lots)</th></tr>
      <tr><td>28/10/2026</td><td>FUTCOM</td><td>GOLDM</td><td>05NOV2026</td>
      <td>141451</td><td>142672</td><td>140555</td><td>142509</td><td>12</td><td>34</td></tr>
      <tr><td>28/10/2026</td><td>FUTCOM</td><td>CRUDEOIL</td><td>19NOV2026</td>
      <td>0</td><td>0</td><td>0</td><td>0</td><td>1</td><td>2</td></tr>
    </table></body></html>
    """
    parser = MODULE.TableParser()
    parser.feed(html)
    converted, symbols = MODULE.canonicalize_rows(parser.tables[0])
    rows = list(__import__("csv").DictReader(__import__("io").StringIO(converted.decode("utf-8"))))
    assert symbols == {"GOLDM"}
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-10-28"
    assert rows[0]["expiry_date"] == "2026-11-05"
    assert rows[0]["close"] == "142509"
    assert rows[0]["volume"] == "12"
    assert rows[0]["open_interest"] == "34"


def test_csv_with_mcx_headers_is_canonicalized():
    raw = "Date,Symbol,Expiry Date,Open,High,Low,Close,Volume(Lots),Open Interest(Lots)\n28/10/2026,GOLDPETAL,31OCT2026,14000,14100,13900,14050,7,9\n"
    converted, symbols = MODULE.canonicalize_rows(list(__import__("csv").reader(__import__("io").StringIO(raw))))
    assert symbols == {"GOLDPETAL"}
    assert b"2026-10-28,GOLDPETAL,2026-10-31" in converted
    assert b"14050" in converted
    assert b",7,9" in converted

def test_mcx_spaced_display_dates_are_normalized_to_iso():
    raw = "Date,Symbol,Expiry Date,Open,High,Low,Close,Volume(Lots),Open Interest(Lots)\n26 Oct 2026,GOLDM,05NOV2026,140511,141800,140333,141451,30036,39046\n"
    converted, symbols = MODULE.canonicalize_rows(list(__import__("csv").reader(__import__("io").StringIO(raw))))
    rows = list(__import__("csv").DictReader(__import__("io").StringIO(converted.decode("utf-8"))))
    assert symbols == {"GOLDM"}
    assert rows[0]["date"] == "2026-10-26"
    assert rows[0]["expiry_date"] == "2026-11-05"
    assert rows[0]["close"] == "141451"


def test_official_page_json_records_are_canonicalized():
    records = [
        {
            "Date": "10/26/2026",
            "Symbol": "GOLDM ",
            "ExpiryDate": "05NOV2026",
            "Open": 141451.0,
            "High": 142672.0,
            "Low": 140555.0,
            "Close": 142509.0,
            "Volume": 12,
            "OpenInterest": 34,
        },
        {
            "Date": "10/26/2026",
            "Symbol": "ALUMINI ",
            "ExpiryDate": "30OCT2026",
            "Open": 328.8,
            "High": 331.7,
            "Low": 327.0,
            "Close": 330.7,
            "Volume": 1238,
            "OpenInterest": 1048,
        },
    ]
    converted, symbols = MODULE.canonicalize_json_records(records)
    rows = list(__import__("csv").DictReader(__import__("io").StringIO(converted.decode("utf-8"))))
    assert symbols == {"GOLDM"}
    assert len(rows) == 1
    assert rows[0]["date"] == "2026-10-26"
    assert rows[0]["expiry_date"] == "2026-11-05"
    assert rows[0]["close"] == "142509.0"
    assert rows[0]["volume"] == "12"
    assert rows[0]["open_interest"] == "34"


def test_json_array_can_be_extracted_from_html_wrapped_page():
    raw = '<html><body><p>[{"Date":"10/26/2026","Symbol":"GOLDM"}]</p></body></html>'
    records = MODULE.find_json_records(raw)
    assert records is not None
    assert records[0]["Symbol"] == "GOLDM"
