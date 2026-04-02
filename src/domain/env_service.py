from __future__ import annotations


class EnvService:
    def __init__(self, app_config):
        self.app_config = app_config

    def read_env(self) -> dict:
        content = ""
        if self.app_config.env_file.exists():
            content = self.app_config.env_file.read_text(encoding="utf-8")
        return {
            "content": content,
            "path": str(self.app_config.env_file),
        }

    def save_env(self, content: str) -> dict:
        self.app_config.env_file.parent.mkdir(parents=True, exist_ok=True)
        self.app_config.env_file.write_text(content or "", encoding="utf-8")
        self.app_config.refresh_from_environment()
        return self.read_env()
