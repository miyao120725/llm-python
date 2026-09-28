def test_health_uses_mock_providers_without_keys(client):
    response = client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["env"] == "development"
    assert body["providers"]["llm"]["mocked"] is True
    assert body["providers"]["image"]["mocked"] is True
    assert body["providers"]["video"]["mocked"] is True


def test_live_and_ready(client):
    live = client.get("/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"
    assert "X-Request-ID" in live.headers

    ready = client.get("/health/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "ok"
    assert body["checks"]["storage"] == "local"
    assert body["checks"]["tasks"] == "sqlite"
    assert body["checks"]["queue"] == "memory"
