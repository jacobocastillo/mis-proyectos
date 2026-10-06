"""
Requirement mapping:
- RNF-08: Availability validation through health and readiness endpoints.
"""


def test_rnf_08_health_and_readiness_reflect_catalog_state(client, seed_catalog):
    health = client.get("/healthz")
    before_ready = client.get("/readyz")

    assert health.status_code == 200
    assert health.get_json() == {"status": "ok"}
    assert before_ready.status_code == 503
    assert before_ready.get_json()["status"] == "not_ready"

    seed_catalog()

    after_ready = client.get("/readyz")
    payload = after_ready.get_json()

    assert after_ready.status_code == 200
    assert payload["status"] == "ready"
    assert payload["checks"]["database"]["ready"] is True
    assert payload["checks"]["catalog"]["ready"] is True
