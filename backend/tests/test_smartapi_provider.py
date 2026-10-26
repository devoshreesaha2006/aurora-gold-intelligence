from datetime import date

from backend.app.providers.smartapi_provider import SmartAPIProvider


def test_mapping_requires_explicit_valid_token_symbol_and_expiry(monkeypatch):
    from backend.app.config import settings

    monkeypatch.setattr(
        settings,
        "smartapi_mcx_token_map",
        '[{"token":"12345","symbol":"GOLDM","expiry_date":"2026-12-05"}]',
    )
    assert SmartAPIProvider()._mapping() == [
        {"token": "12345", "symbol": "GOLDM", "expiry_date": "2026-12-05"}
    ]


def test_mapping_rejects_duplicate_tokens(monkeypatch):
    from backend.app.config import settings

    monkeypatch.setattr(
        settings,
        "smartapi_mcx_token_map",
        '[{"token":"12345","symbol":"GOLDM","expiry_date":"2026-12-05"},'
        '{"token":"12345","symbol":"GOLDM","expiry_date":"2027-02-05"}]',
    )
    assert SmartAPIProvider()._mapping() == []


def test_mapping_rejects_non_numeric_tokens_and_invalid_expiry(monkeypatch):
    from backend.app.config import settings

    monkeypatch.setattr(
        settings,
        "smartapi_mcx_token_map",
        '[{"token":"TOKEN","symbol":"GOLDM","expiry_date":"not-a-date"}]',
    )
    assert SmartAPIProvider()._mapping() == []
