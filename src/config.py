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
    database_file: Path
    history_file: Path
    groups_file: Path
    registered_courses_file: Path
    env_file: Path
    app_log_file: Path
    scheduler_enabled: bool = True
    scheduler_poll_seconds: int = 30

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
        database_file = data_dir / "canvas_bulk_panel.db"
        database_url = _first_non_empty(
            _resolve_env_value("DATABASE_URL", env_values),
            _resolve_env_value("MYSQL_URL", env_values),
            f"sqlite:///{database_file.as_posix()}",
        )

        default_access_token = _first_non_empty(
            _resolve_env_value("CANVAS_ACCESS_TOKEN", env_values),
            _resolve_env_value("CANVAS_PERSONAL_ACCESS_TOKEN", env_values),
            _resolve_env_value("CANVAS_API_TOKEN", env_values),
        )

        default_token_source = "none"
        if _resolve_env_value("CANVAS_ACCESS_TOKEN", env_values):
            default_token_source = "access_token"
        elif _resolve_env_value("CANVAS_PERSONAL_ACCESS_TOKEN", env_values):
            default_token_source = "personal_access_token"
        elif _resolve_env_value("CANVAS_API_TOKEN", env_values):
            default_token_source = "api_token"

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
            scheduler_enabled=_env_bool("SCHEDULER_ENABLED", True),
            scheduler_poll_seconds=int(_first_non_empty(_resolve_env_value("SCHEDULER_POLL_SECONDS", env_values), "30")),
            legacy_json_import_enabled=_env_bool("ENABLE_LEGACY_JSON_IMPORT", False),
            default_base_url=_resolve_env_value("CANVAS_BASE_URL", env_values),
            default_access_token=default_access_token,
            default_token_source=default_token_source,
            code_root=packaged_root,
            runtime_root=runtime_root,
            templates_dir=packaged_root / "templates",
            static_dir=packaged_root / "static",
            data_dir=data_dir,
            reports_dir=reports_dir,
            logs_dir=logs_dir,
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

        default_access_token = _first_non_empty(
            _resolve_env_value("CANVAS_ACCESS_TOKEN", env_values),
            _resolve_env_value("CANVAS_PERSONAL_ACCESS_TOKEN", env_values),
            _resolve_env_value("CANVAS_API_TOKEN", env_values),
        )
        self.default_access_token = default_access_token

        default_token_source = "none"
        if _resolve_env_value("CANVAS_ACCESS_TOKEN", env_values):
            default_token_source = "access_token"
        elif _resolve_env_value("CANVAS_PERSONAL_ACCESS_TOKEN", env_values):
            default_token_source = "personal_access_token"
        elif _resolve_env_value("CANVAS_API_TOKEN", env_values):
            default_token_source = "api_token"
        self.default_token_source = default_token_source

        self.request_timeout = int(_first_non_empty(_resolve_env_value("CANVAS_REQUEST_TIMEOUT", env_values), str(self.request_timeout)))
        self.retry_max_attempts = int(_first_non_empty(_resolve_env_value("CANVAS_RETRY_MAX_ATTEMPTS", env_values), str(self.retry_max_attempts)))
        self.retry_base_delay = float(_first_non_empty(_resolve_env_value("CANVAS_RETRY_BASE_DELAY", env_values), str(self.retry_base_delay)))
        self.history_limit = int(_first_non_empty(_resolve_env_value("HISTORY_LIMIT", env_values), str(self.history_limit)))
        self.scheduler_enabled = _env_bool("SCHEDULER_ENABLED", self.scheduler_enabled)
        self.scheduler_poll_seconds = int(_first_non_empty(_resolve_env_value("SCHEDULER_POLL_SECONDS", env_values), str(self.scheduler_poll_seconds)))
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
            "database_backend": database_backend,
            "database_url_masked": self._mask_database_url(),
            "request_timeout": self.request_timeout,
            "retry_max_attempts": self.retry_max_attempts,
            "retry_base_delay": self.retry_base_delay,
            "history_limit": self.history_limit,
            "scheduler_enabled": self.scheduler_enabled,
            "scheduler_poll_seconds": self.scheduler_poll_seconds,
            "legacy_json_import_enabled": self.legacy_json_import_enabled,
            "env_file_path": str(self.env_file),
            "env_file_name": self.env_file.name,
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
