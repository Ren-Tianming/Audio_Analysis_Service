from app.api.routes import songs
from fastapi.testclient import TestClient


def register(client: TestClient, email: str) -> tuple[str, dict]:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": "制作者",
            "password": "secure-pass-123",
            "password_confirmation": "secure-pass-123",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["refresh_token"]
    return body["access_token"], body["user"]


def headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def fake_analysis(_: object) -> dict:
    return {
        "file_format": "wav",
        "duration_sec": 3.0,
        "sample_rate": 44100,
        "channels": 2,
        "bpm": 128.0,
        "musical_key": "F# マイナー",
        "rms": 0.124,
        "lufs": -12.4,
        "waveform": [0.1, -0.1],
        "spectrogram": [[-20.0, -10.0]],
    }


def test_register_and_daily_login_bonus_are_recorded_once(client: TestClient) -> None:
    _, user = register(client, "bonus@example.com")
    assert user["points_balance"] == 20

    first = client.post("/api/v1/auth/login", json={"email": "bonus@example.com", "password": "secure-pass-123"})
    second = client.post("/api/v1/auth/login", json={"email": "bonus@example.com", "password": "secure-pass-123"})
    assert first.json()["refresh_token"] != second.json()["refresh_token"]
    assert first.json()["daily_bonus_awarded"] == 10
    assert first.json()["user"]["points_balance"] == 30
    assert second.json()["daily_bonus_awarded"] == 0
    assert second.json()["user"]["points_balance"] == 30

    ledger = client.get("/api/v1/points/transactions", headers=headers(second.json()["access_token"])).json()
    assert {entry["transaction_type"] for entry in ledger} == {"REGISTER_BONUS", "DAILY_LOGIN_BONUS"}


def test_operational_endpoints_expose_readiness_request_id_and_metrics(client: TestClient) -> None:
    ready = client.get("/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"]["database"] == "ok"
    health = client.get("/health", headers={"X-Request-ID": "test-trace-id"})
    assert health.headers["X-Request-ID"] == "test-trace-id"
    metrics = client.get("/metrics")
    assert "aas_http_requests_total" in metrics.text


def test_successful_analysis_consumes_points_and_protects_ownership(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(songs, "analyze_audio", fake_analysis)
    owner_token, _ = register(client, "tracks@example.com")
    other_token, _ = register(client, "other@example.com")
    response = client.post(
        "/api/v1/songs/analyze",
        files={"file": ("pulse.wav", b"test-signal", "audio/wav")},
        headers=headers(owner_token),
    )
    assert response.status_code == 201
    assert response.json()["points_cost"] == 5
    analysis_id = response.json()["id"]
    assert client.get(f"/api/v1/songs/history/{analysis_id}", headers=headers(other_token)).status_code == 404
    assert client.get("/api/v1/points/balance", headers=headers(owner_token)).json()["points_balance"] == 15


def test_analysis_does_not_start_without_points(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(songs, "analyze_audio", fake_analysis)
    token, _ = register(client, "empty@example.com")
    for index in range(4):
        result = client.post(
            "/api/v1/songs/analyze",
            files={"file": (f"pulse-{index}.wav", b"test-signal", "audio/wav")},
            headers=headers(token),
        )
        assert result.status_code == 201
    rejected = client.post(
        "/api/v1/songs/analyze",
        files={"file": ("too-many.wav", b"test-signal", "audio/wav")},
        headers=headers(token),
    )
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "INSUFFICIENT_POINTS"


def test_mock_payment_is_idempotent_and_api_key_is_shown_once(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(songs, "analyze_audio", fake_analysis)
    token, _ = register(client, "commerce@example.com")
    packages = client.get("/api/v1/pricing/packages").json()
    order = client.post("/api/v1/orders", json={"package_id": packages[0]["id"]}, headers=headers(token)).json()
    paid = client.post(f"/api/v1/orders/{order['id']}/mock-pay", headers=headers(token))
    duplicate = client.post(f"/api/v1/orders/{order['id']}/mock-pay", headers=headers(token))
    assert paid.status_code == 200
    assert duplicate.status_code == 409
    assert client.get("/api/v1/points/balance", headers=headers(token)).json()["points_balance"] == 120

    issued = client.post("/api/v1/api-keys", json={"name": "DAW 連携"}, headers=headers(token)).json()
    listed = client.get("/api/v1/api-keys", headers=headers(token)).json()
    assert issued["api_key"].startswith("aas_")
    assert "api_key" not in listed[0]

    analyzed = client.post(
        "/api/v1/songs/analyze",
        files={"file": ("api-track.wav", b"test-signal", "audio/wav")},
        headers={"X-API-Key": issued["api_key"]},
    )
    usage = client.get("/api/v1/api-keys/usage", headers=headers(token)).json()
    assert analyzed.status_code == 201
    assert usage[0]["status_code"] == 201
    assert usage[0]["points_cost"] == 5


def test_refresh_token_rotation_and_logout_all(client: TestClient) -> None:
    initial = client.post(
        "/api/v1/auth/register",
        json={
            "email": "rotation@example.com",
            "username": "制作者",
            "password": "secure-pass-123",
            "password_confirmation": "secure-pass-123",
        },
    ).json()
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": initial["refresh_token"]})
    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != initial["refresh_token"]

    reused = client.post("/api/v1/auth/refresh", json={"refresh_token": initial["refresh_token"]})
    assert reused.status_code == 401
    assert reused.json()["error"]["code"] == "REFRESH_TOKEN_REUSED"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "rotation@example.com", "password": "secure-pass-123"},
    ).json()
    logout = client.post("/api/v1/auth/logout-all", headers=headers(login["access_token"]))
    assert logout.status_code == 200
    rejected = client.post("/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]})
    assert rejected.status_code == 401
