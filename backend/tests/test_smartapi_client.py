import httpx
import pytest

from backend.app.providers.smartapi_client import (
    SMARTAPI_QUOTE_URL,
    SmartAPIError,
    SmartAPIMarketDataClient,
)


def _client(handler):
    return SmartAPIMarketDataClient(
        api_key="test-key",
        jwt_token="test-jwt",
        client_code="TEST001",
        local_ip="127.0.0.1",
        public_ip="203.0.113.10",
        mac_address="00:11:22:33:44:55",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_fetch_full_mcx_quotes_sends_tokens_server_side_and_returns_only_fetched_mcx():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = request.read().decode()
        return httpx.Response(200, json={
            "status": True,
            "data": {
                "fetched": [
                    {"exchange": "MCX", "tradingSymbol": "GOLDM26DEC", "symbolToken": "123", "ltp": 62500, "openInterest": 450},
                    {"exchange": "NSE", "tradingSymbol": "ABC", "symbolToken": "456", "ltp": 100},
                ],
                "unfetched": [],
            },
        })

    client = _client(handler)
    rows = client.fetch_full_mcx_quotes(["123", "123", "456"])

    assert seen["url"] == SMARTAPI_QUOTE_URL
    assert seen["headers"]["authorization"] == "Bearer test-jwt"
    assert seen["headers"]["x-privatekey"] == "test-key"
    assert '"MCX":["123","456"]' in seen["body"].replace(" ", "")
    assert len(rows) == 1
    assert rows[0]["tradingSymbol"] == "GOLDM26DEC"


def test_fetch_full_mcx_quotes_rejects_more_than_50_tokens():
    client = _client(lambda request: httpx.Response(200, json={"status": True, "data": {"fetched": []}}))
    with pytest.raises(ValueError, match="at most 50"):
        client.fetch_full_mcx_quotes([str(i) for i in range(51)])


def test_fetch_full_mcx_quotes_does_not_expose_response_body_on_failure():
    client = _client(lambda request: httpx.Response(401, text="private auth detail"))
    with pytest.raises(SmartAPIError, match="request failed") as exc:
        client.fetch_full_mcx_quotes(["123"])
    assert "private auth detail" not in str(exc.value)
