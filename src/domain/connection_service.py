from __future__ import annotations

from src.services.canvas_client import CanvasClient
from src.utils.parsing import mask_token, normalize_base_url


class ConnectionService:
    def __init__(self, app_config):
        self.app_config = app_config

    def resolve_credentials(self, payload: dict) -> dict:
        base_url = normalize_base_url(payload.get("base_url") or self.app_config.default_base_url)
        access_token = (
            payload.get("access_token")
            or payload.get("api_token")
            or self.app_config.default_access_token
        ).strip()
        token_type = (payload.get("token_type") or "personal").strip() or "personal"

        if not base_url:
            raise ValueError(
                "Informe a URL base do Canvas, por exemplo "
                "`https://sua-instituicao.instructure.com` ou `https://sua-instituicao.test.instructure.com`, "
                "ou configure `CANVAS_BASE_URL` no `.env`."
            )
        if not access_token:
            raise ValueError(
                "Informe um `token de acesso` ou configure `CANVAS_ACCESS_TOKEN`, "
                "`CANVAS_PERSONAL_ACCESS_TOKEN` ou `CANVAS_API_TOKEN` no `.env`."
            )

        return {
            "base_url": base_url,
            "access_token": access_token,
            "token_type": token_type,
        }

    def build_client(self, payload: dict) -> CanvasClient:
        credentials = self.resolve_credentials(payload)
        return CanvasClient(
            base_url=credentials["base_url"],
            access_token=credentials["access_token"],
            timeout=self.app_config.request_timeout,
            retry_max_attempts=self.app_config.retry_max_attempts,
            retry_base_delay=self.app_config.retry_base_delay,
        )

    def test_connection(self, payload: dict) -> dict:
        credentials = self.resolve_credentials(payload)
        client = self.build_client(credentials)
        user = client.get_current_user()

        return {
            "ok": True,
            "base_url": credentials["base_url"],
            "used_env_token": not bool(payload.get("access_token") or payload.get("api_token")),
            "masked_token": mask_token(credentials["access_token"]),
            "token_type": credentials["token_type"],
            "env_token_source": self.app_config.default_token_source,
            "user": {
                "id": user.get("id"),
                "name": user.get("name") or user.get("short_name"),
                "sortable_name": user.get("sortable_name"),
                "avatar_url": user.get("avatar_url"),
            },
        }
