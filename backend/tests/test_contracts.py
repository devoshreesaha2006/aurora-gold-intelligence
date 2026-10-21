from backend.app.services.normalization import normalize_price


def test_list_contracts(client):
    response = client.get("/api/contracts")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    contracts = data["data"]
    symbols = [c["symbol"] for c in contracts]
    assert "GOLDM" in symbols
    assert "GOLDTEN" in symbols
    assert "GOLDGUINEA" in symbols
    assert "GOLDPETAL" in symbols


def test_contract_normalization_logic():
    # GOLDM: 62450 per 10g at 995 purity
    norm_gram, norm_10g = normalize_price(
        quoted_price=62450.0,
        quote_unit_grams=10.0,
        purity_factor=0.995
    )
    # 62450 / 10 = 6245. 6245 / 0.995 = 6276.3819
    assert abs(norm_gram - 6276.3819) < 0.01
    assert abs(norm_10g - 62450.0) < 0.01

    # GOLDGUINEA: 50120 per 8g at 999 purity
    norm_gram_g, norm_10g_g = normalize_price(
        quoted_price=50120.0,
        quote_unit_grams=8.0,
        purity_factor=0.999
    )
    # 50120 / 8 = 6265. 6265 / 0.999 = 6271.2713
    assert abs(norm_gram_g - 6271.2713) < 0.01
    assert abs(norm_10g_g - 62399.15) < 0.05
