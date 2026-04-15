from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values, load_dotenv


def _env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _first_non_empty(*values):
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _resolve_env_value(name: str, env_values: dict[str, str], default: str = "") -> str:
    process_value = os.getenv(name)
    if process_value is not None and str(process_value).strip():
        return str(process_value).strip()
    file_value = env_values.get(name)
    if file_value is not None and str(file_value).strip():
        return str(file_value).strip()
    return default


def _normalize_canvas_environment(value: str | None) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"test", "teste", "testing", "beta", "sandbox"}:
        return "test"
    return "real"


def _resolve_canvas_token(env_values: dict[str, str], *, suffix: str = "") -> tuple[str, str]:
    token_names = [
        (f"CANVAS_ACCESS_TOKEN{suffix}", f"access_token{suffix.lower()}"),
        (f"CANVAS_PERSONAL_ACCESS_TOKEN{suffix}", f"personal_access_token{suffix.lower()}"),
        (f"CANVAS_API_TOKEN{suffix}", f"api_token{suffix.lower()}"),
    ]
    for env_name, source in token_names:
        if _resolve_env_value(env_name, env_values):
            return _resolve_env_value(env_name, env_values), source
    return "", "none"


@dataclass(slots=True)
class AppConfig:
    host: str
    port: int
    debug: bool
    database_url: str
    database_echo: bool
    request_timeout: int
    retry_max_attempts: int
    retry_base_delay: float
    history_limit: int
    legacy_json_import_enabled: bool
    default_base_url: str
    default_access_token: str
    default_token_source: str
    code_root: Path
    runtime_root: Path
    templates_dir: Path
    static_dir: Path
    data_dir: Path
    reports_dir: Path
    logs_dir: Path
    uploads_dir: Path
    database_file: Path
    history_file: Path
    groups_file: Path
    registered_courses_file: Path
    env_file: Path
    app_log_file: Path
    test_base_url: str = ""
    test_access_token: str = ""
    test_token_source: str = "none"
    default_canvas_environment: str = "real"
    panel_idle_shutdown_enabled: bool = False
    panel_idle_timeout_seconds: int = 10800
    panel_idle_check_interval_seconds: int = 60
    panel_idle_activity_file: Path = Path("/tmp/canvas-bulk-panel.last-activity")

    @classmethod
    def from_env(cls) -> "AppConfig":
        packaged_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
        runtime_root = (
            Path(sys.executable).resolve().parent
            if getattr(sys, "frozen", False)
            else packaged_root
        )
        env_override = os.getenv("CANVAS_PANEL_ENV_FILE", "").strip()
        env_file = Path(env_override).expanduser() if env_override else (runtime_root / ".env")
        env_values = {
            key: str(value)
            for key, value in dotenv_values(env_file).items()
            if value is not None
        }
        load_dotenv(env_file, override=False)

        data_dir = Path(os.getenv("CANVAS_PANEL_DATA_DIR", runtime_root / "data"))
        logs_dir = Path(os.getenv("CANVAS_PANEL_LOGS_DIR", runtime_root / "logs"))
        reports_dir = data_dir / "reports"
        uploads_dir = data_dir / "uploads"
        database_file = data_dir / "canvas_bulk_panel.db"
        database_url = _first_non_empty(
            _resolve_env_value("DATABASE_URL", env_values),
            _resolve_env_value("MYSQL_URL", env_values),
            f"sqlite:///{database_file.as_posix()}",
        )

        default_access_token, default_token_source = _resolve_canvas_token(env_values)
        test_access_token, test_token_source = _resolve_canvas_token(env_values, suffix="_TEST")

        return cls(
            host=os.getenv("FLASK_HOST", "127.0.0.1"),
            port=int(os.getenv("FLASK_PORT", "5000")),
            debug=_env_bool("FLASK_DEBUG", False),
            database_url=database_url,
            database_echo=_env_bool("DATABASE_ECHO", False),
            request_timeout=int(_first_non_empty(_resolve_env_value("CANVAS_REQUEST_TIMEOUT", env_values), "30")),
            retry_max_attempts=int(_first_non_empty(_resolve_env_value("CANVAS_RETRY_MAX_ATTEMPTS", env_values), "4")),
            retry_base_delay=float(_first_non_empty(_resolve_env_value("CANVAS_RETRY_BASE_DELAY", env_values), "1.5")),
            history_limit=int(_first_non_empty(_resolve_env_value("HISTORY_LIMIT", env_values), "25")),
            legacy_json_import_enabled=_env_bool("ENABLE_LEGACY_JSON_IMPORT", False),
            default_base_url=_resolve_env_value("CANVAS_BASE_URL", env_values),
            default_access_token=default_access_token,
            default_token_source=default_token_source,
            test_base_url=_resolve_env_value("CANVAS_BASE_URL_TEST", env_values),
            test_access_token=test_access_token,
            test_token_source=test_token_source,
            default_canvas_environment=_normalize_canvas_environment(_resolve_env_value("CANVAS_ENVIRONMENT", env_values)),
            panel_idle_shutdown_enabled=_env_bool("PANEL_IDLE_SHUTDOWN_ENABLED", False),
            panel_idle_timeout_seconds=int(_first_non_empty(_resolve_env_value("PANEL_IDLE_TIMEOUT_SECONDS", env_values), "10800")),
            panel_idle_check_interval_seconds=int(_first_non_empty(_resolve_env_value("PANEL_IDLE_CHECK_INTERVAL_SECONDS", env_values), "60")),
            panel_idle_activity_file=Path(_first_non_empty(_resolve_env_value("PANEL_IDLE_ACTIVITY_FILE", env_values), "/tmp/canvas-bulk-panel.last-activity")),
            code_root=packaged_root,
            runtime_root=runtime_root,
            templates_dir=packaged_root / "templates",
            static_dir=packaged_root / "static",
            data_dir=data_dir,
            reports_dir=reports_dir,
            logs_dir=logs_dir,
            uploads_dir=uploads_dir,
            database_file=database_file,
            history_file=data_dir / "history.json",
            groups_file=data_dir / "course_groups.json",
            registered_courses_file=data_dir / "registered_courses.json",
            env_file=env_file,
            app_log_file=logs_dir / "app.log",
        )

    def ensure_runtime_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)

        if not self.history_file.exists():
            self.history_file.write_text("[]\n", encoding="utf-8")

        if not self.groups_file.exists():
            self.groups_file.write_text("[]\n", encoding="utf-8")

        if not self.registered_courses_file.exists():
            self.registered_courses_file.write_text("[]\n", encoding="utf-8")

        if not self.app_log_file.exists():
            self.app_log_file.write_text("", encoding="utf-8")

    def refresh_from_environment(self) -> None:
        env_values = {
            key: str(value)
            for key, value in dotenv_values(self.env_file).items()
            if value is not None
        }
        load_dotenv(self.env_file, override=True)

        self.default_base_url = _resolve_env_value("CANVAS_BASE_URL", env_values)

        default_access_token, default_token_source = _resolve_canvas_token(env_values)
        self.default_access_token = default_access_token
        self.default_token_source = default_token_source
        test_access_token, test_token_source = _resolve_canvas_token(env_values, suffix="_TEST")
        self.test_base_url = _resolve_env_value("CANVAS_BASE_URL_TEST", env_values)
        self.test_access_token = test_access_token
        self.test_token_source = test_token_source
        self.default_canvas_environment = _normalize_canvas_environment(_resolve_env_value("CANVAS_ENVIRONMENT", env_values))
        self.panel_idle_shutdown_enabled = _env_bool("PANEL_IDLE_SHUTDOWN_ENABLED", self.panel_idle_shutdown_enabled)
        self.panel_idle_timeout_seconds = int(_first_non_empty(_resolve_env_value("PANEL_IDLE_TIMEOUT_SECONDS", env_values), str(self.panel_idle_timeout_seconds)))
        self.panel_idle_check_interval_seconds = int(_first_non_empty(_resolve_env_value("PANEL_IDLE_CHECK_INTERVAL_SECONDS", env_values), str(self.panel_idle_check_interval_seconds)))
        self.panel_idle_activity_file = Path(_first_non_empty(_resolve_env_value("PANEL_IDLE_ACTIVITY_FILE", env_values), str(self.panel_idle_activity_file)))

        self.request_timeout = int(_first_non_empty(_resolve_env_value("CANVAS_REQUEST_TIMEOUT", env_values), str(self.request_timeout)))
        self.retry_max_attempts = int(_first_non_empty(_resolve_env_value("CANVAS_RETRY_MAX_ATTEMPTS", env_values), str(self.retry_max_attempts)))
        self.retry_base_delay = float(_first_non_empty(_resolve_env_value("CANVAS_RETRY_BASE_DELAY", env_values), str(self.retry_base_delay)))
        self.history_limit = int(_first_non_empty(_resolve_env_value("HISTORY_LIMIT", env_values), str(self.history_limit)))
        self.database_url = _first_non_empty(
            _resolve_env_value("DATABASE_URL", env_values),
            _resolve_env_value("MYSQL_URL", env_values),
            self.database_url,
        )
        self.database_echo = _env_bool("DATABASE_ECHO", self.database_echo)

    def public_settings(self) -> dict:
        database_backend = "mysql" if self.database_url.lower().startswith("mysql") else "sqlite"
        return {
            "default_base_url": self.default_base_url,
            "env_token_available": bool(self.default_access_token),
            "env_token_source": self.default_token_source,
            "active_environment": self.default_canvas_environment,
            "canvas_environments": {
                "real": self.canvas_environment_settings("real"),
                "test": self.canvas_environment_settings("test"),
            },
            "database_backend": database_backend,
            "database_url_masked": self._mask_database_url(),
            "request_timeout": self.request_timeout,
            "retry_max_attempts": self.retry_max_attempts,
            "retry_base_delay": self.retry_base_delay,
            "panel_idle_shutdown_enabled": self.panel_idle_shutdown_enabled,
            "panel_idle_timeout_seconds": self.panel_idle_timeout_seconds,
            "panel_idle_check_interval_seconds": self.panel_idle_check_interval_seconds,
            "panel_idle_activity_file": str(self.panel_idle_activity_file),
            "history_limit": self.history_limit,
            "legacy_json_import_enabled": self.legacy_json_import_enabled,
            "env_file_path": str(self.env_file),
            "env_file_name": self.env_file.name,
        }

    def canvas_environment_settings(self, environment: str) -> dict:
        key = _normalize_canvas_environment(environment)
        if key == "test":
            return {
                "key": "test",
                "label": "Ambiente de teste",
                "base_url_var": "CANVAS_BASE_URL_TEST",
                "token_var": self.test_token_source,
                "default_base_url": self.test_base_url,
                "env_token_available": bool(self.test_access_token),
                "env_token_source": self.test_token_source,
            }
        return {
            "key": "real",
            "label": "Ambiente real",
            "base_url_var": "CANVAS_BASE_URL",
            "token_var": self.default_token_source,
            "default_base_url": self.default_base_url,
            "env_token_available": bool(self.default_access_token),
            "env_token_source": self.default_token_source,
        }

    def canvas_credentials_for_environment(self, environment: str) -> dict:
        key = _normalize_canvas_environment(environment)
        if key == "test":
            return {
                "environment": "test",
                "base_url": self.test_base_url,
                "access_token": self.test_access_token,
                "token_source": self.test_token_source,
            }
        return {
            "environment": "real",
            "base_url": self.default_base_url,
            "access_token": self.default_access_token,
            "token_source": self.default_token_source,
        }

    def _mask_database_url(self) -> str:
        if "://" not in self.database_url:
            return self.database_url
        scheme, rest = self.database_url.split("://", 1)
        if "@" not in rest:
            return f"{scheme}://{rest}"
        credentials, tail = rest.split("@", 1)
        if ":" not in credentials:
            return f"{scheme}://***@{tail}"
        username, _password = credentials.split(":", 1)
        return f"{scheme}://{username}:***@{tail}"
