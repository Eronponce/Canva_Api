from __future__ import annotations

from pathlib import Path

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


def test_config_exposes_docker_idle_shutdown_settings(isolated_env, monkeypatch):
    activity_file = Path(isolated_env["data_dir"]) / "idle" / "last-activity.txt"
    monkeypatch.setenv("PANEL_IDLE_SHUTDOWN_ENABLED", "true")
    monkeypatch.setenv("PANEL_IDLE_TIMEOUT_SECONDS", "10800")
    monkeypatch.setenv("PANEL_IDLE_CHECK_INTERVAL_SECONDS", "60")
    monkeypatch.setenv("PANEL_IDLE_ACTIVITY_FILE", str(activity_file))

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/api/config")

    assert response.status_code == 200
    settings = response.get_json()["settings"]
    assert settings["panel_idle_shutdown_enabled"] is True
    assert settings["panel_idle_timeout_seconds"] == 10800
    assert settings["panel_idle_check_interval_seconds"] == 60
    assert settings["panel_idle_activity_file"] == str(activity_file)


def test_healthz_does_not_refresh_idle_activity_marker(isolated_env, monkeypatch):
    activity_file = Path(isolated_env["data_dir"]) / "idle" / "last-activity.txt"
    monkeypatch.setenv("PANEL_IDLE_SHUTDOWN_ENABLED", "true")
    monkeypatch.setenv("PANEL_IDLE_ACTIVITY_FILE", str(activity_file))

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    initial_marker = activity_file.read_text(encoding="utf-8")

    health_response = client.get("/healthz")

    assert health_response.status_code == 200
    assert health_response.get_json() == {"status": "ok"}
    assert activity_file.read_text(encoding="utf-8") == initial_marker

    config_response = client.get("/api/config")

    assert config_response.status_code == 200
    assert activity_file.read_text(encoding="utf-8") != initial_marker
