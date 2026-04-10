from __future__ import annotations

from src.app_factory import create_app


def test_connection_endpoint_requires_base_url(client):
    response = client.post(
        "/api/connection/test",
        json={
            "access_token": "token-123",
            "token_type": "personal",
        },
    )

    assert response.status_code == 400
    assert "URL base do Canvas" in response.get_json()["error"]


def test_config_exposes_env_token_source_alias(isolated_env, monkeypatch):
    monkeypatch.setenv("CANVAS_BASE_URL", "https://canvas.example.com")
    monkeypatch.setenv("CANVAS_PERSONAL_ACCESS_TOKEN", "personal-token")

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/api/config")

    assert response.status_code == 200
    settings = response.get_json()["settings"]
    assert settings["default_base_url"] == "https://canvas.example.com"
    assert settings["env_token_available"] is True
    assert settings["env_token_source"] == "personal_access_token"


def test_config_exposes_test_canvas_environment(isolated_env, monkeypatch):
    monkeypatch.setenv("CANVAS_BASE_URL", "https://canvas.example.com")
    monkeypatch.setenv("CANVAS_ACCESS_TOKEN", "real-token")
    monkeypatch.setenv("CANVAS_BASE_URL_TEST", "https://canvas.test.example.com")
    monkeypatch.setenv("CANVAS_ACCESS_TOKEN_TEST", "test-token")
    monkeypatch.setenv("CANVAS_ENVIRONMENT", "test")

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/api/config")

    assert response.status_code == 200
    settings = response.get_json()["settings"]
    assert settings["active_environment"] == "test"
    assert settings["canvas_environments"]["real"]["default_base_url"] == "https://canvas.example.com"
    assert settings["canvas_environments"]["real"]["env_token_source"] == "access_token"
    assert settings["canvas_environments"]["test"]["default_base_url"] == "https://canvas.test.example.com"
    assert settings["canvas_environments"]["test"]["env_token_available"] is True
    assert settings["canvas_environments"]["test"]["env_token_source"] == "access_token_test"

    credentials = app.extensions["services"]["connection_service"].resolve_credentials(
        {"canvas_environment": "test", "token_type": "personal"}
    )
    assert credentials["canvas_environment"] == "test"
    assert credentials["base_url"] == "https://canvas.test.example.com"
    assert credentials["access_token"] == "test-token"
    assert credentials["env_token_source"] == "access_token_test"
