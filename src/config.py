from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class AppConfig:
    host: str
    port: int
    debug: bool
    request_timeout: int
    retry_max_attempts: int
    retry_base_delay: float
    history_limit: int
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
    history_file: Path
    groups_file: Path
    registered_courses_file: Path
    env_file: Path
    app_log_file: Path

    @classmethod
    def from_env(cls) -> "AppConfig":
        packaged_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
        runtime_root = (
            Path(sys.executable).resolve().parent
            if getattr(sys, "frozen", False)
            else packaged_root
        )

        data_dir = Path(os.getenv("CANVAS_PANEL_DATA_DIR", runtime_root / "data"))
        logs_dir = Path(os.getenv("CANVAS_PANEL_LOGS_DIR", runtime_root / "logs"))
        reports_dir = data_dir / "reports"

        default_access_token = (
            os.getenv("CANVAS_ACCESS_TOKEN")
            or os.getenv("CANVAS_PERSONAL_ACCESS_TOKEN")
            or os.getenv("CANVAS_API_TOKEN")
            or ""
        ).strip()

        default_token_source = "none"
        if os.getenv("CANVAS_ACCESS_TOKEN", "").strip():
            default_token_source = "access_token"
        elif os.getenv("CANVAS_PERSONAL_ACCESS_TOKEN", "").strip():
            default_token_source = "personal_access_token"
        elif os.getenv("CANVAS_API_TOKEN", "").strip():
            default_token_source = "api_token"

        env_file = runtime_root / ".env"

        return cls(
            host=os.getenv("FLASK_HOST", "127.0.0.1"),
            port=int(os.getenv("FLASK_PORT", "5000")),
            debug=_env_bool("FLASK_DEBUG", False),
            request_timeout=int(os.getenv("CANVAS_REQUEST_TIMEOUT", "30")),
            retry_max_attempts=int(os.getenv("CANVAS_RETRY_MAX_ATTEMPTS", "4")),
            retry_base_delay=float(os.getenv("CANVAS_RETRY_BASE_DELAY", "1.5")),
            history_limit=int(os.getenv("HISTORY_LIMIT", "25")),
            default_base_url=os.getenv("CANVAS_BASE_URL", "").strip(),
            default_access_token=default_access_token,
            default_token_source=default_token_source,
            code_root=packaged_root,
            runtime_root=runtime_root,
            templates_dir=packaged_root / "templates",
            static_dir=packaged_root / "static",
            data_dir=data_dir,
            reports_dir=reports_dir,
            logs_dir=logs_dir,
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
        load_dotenv(self.env_file, override=True)

        self.default_base_url = os.getenv("CANVAS_BASE_URL", "").strip()

        default_access_token = (
            os.getenv("CANVAS_ACCESS_TOKEN")
            or os.getenv("CANVAS_PERSONAL_ACCESS_TOKEN")
            or os.getenv("CANVAS_API_TOKEN")
            or ""
        ).strip()
        self.default_access_token = default_access_token

        default_token_source = "none"
        if os.getenv("CANVAS_ACCESS_TOKEN", "").strip():
            default_token_source = "access_token"
        elif os.getenv("CANVAS_PERSONAL_ACCESS_TOKEN", "").strip():
            default_token_source = "personal_access_token"
        elif os.getenv("CANVAS_API_TOKEN", "").strip():
            default_token_source = "api_token"
        self.default_token_source = default_token_source

        self.request_timeout = int(os.getenv("CANVAS_REQUEST_TIMEOUT", str(self.request_timeout)))
        self.retry_max_attempts = int(
            os.getenv("CANVAS_RETRY_MAX_ATTEMPTS", str(self.retry_max_attempts))
        )
        self.retry_base_delay = float(
            os.getenv("CANVAS_RETRY_BASE_DELAY", str(self.retry_base_delay))
        )
        self.history_limit = int(os.getenv("HISTORY_LIMIT", str(self.history_limit)))

    def public_settings(self) -> dict:
        return {
            "default_base_url": self.default_base_url,
            "env_token_available": bool(self.default_access_token),
            "env_token_source": self.default_token_source,
            "request_timeout": self.request_timeout,
            "retry_max_attempts": self.retry_max_attempts,
            "retry_base_delay": self.retry_base_delay,
            "history_limit": self.history_limit,
            "env_file_path": str(self.env_file),
        }
