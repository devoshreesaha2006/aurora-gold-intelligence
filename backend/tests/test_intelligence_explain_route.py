"""Regression coverage for the Historical Intelligence explain endpoint."""

def test_explain_route_does_not_require_scenario_helper_parameters(client):
    # With the test database seeded but no historical observations, the route may
    # return 404. It must not return FastAPI's 422 missing-query-parameter error.
    response = client.get(
        "/api/intelligence/explain",
        params={"pair": "GOLDM-GOLDPETAL", "window": 30},
    )
    assert response.status_code in (200, 404), response.text


def test_explain_route_accepts_optional_evaluation_date(client):
    response = client.get(
        "/api/intelligence/explain",
        params={
            "pair": "GOLDM-GOLDPETAL",
            "window": 30,
            "evaluation_date": "2026-10-01",
        },
    )
    assert response.status_code in (200, 404), response.text
