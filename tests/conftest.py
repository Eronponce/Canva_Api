from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.app_factory import create_app


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    logs_dir = tmp_path / "logs"
    env_file = tmp_path / ".env"
    monkeypatch.setenv("CANVAS_PANEL_DATA_DIR", str(data_dir))
    monkeypatch.setenv("CANVAS_PANEL_LOGS_DIR", str(logs_dir))
    monkeypatch.setenv("CANVAS_PANEL_ENV_FILE", str(env_file))
    monkeypatch.delenv("CANVAS_BASE_URL", raising=False)
    monkeypatch.delenv("CANVAS_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("CANVAS_PERSONAL_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("CANVAS_API_TOKEN", raising=False)
    monkeypatch.delenv("CANVAS_BASE_URL_TEST", raising=False)
    monkeypatch.delenv("CANVAS_ACCESS_TOKEN_TEST", raising=False)
    monkeypatch.delenv("CANVAS_PERSONAL_ACCESS_TOKEN_TEST", raising=False)
    monkeypatch.delenv("CANVAS_API_TOKEN_TEST", raising=False)
    monkeypatch.delenv("CANVAS_ENVIRONMENT", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("MYSQL_URL", raising=False)
    monkeypatch.setenv("SCHEDULER_ENABLED", "0")
    return {"data_dir": data_dir, "logs_dir": logs_dir, "env_file": env_file}


@pytest.fixture
def app(isolated_env):
    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()
