from __future__ import annotations

import json
from pathlib import Path

from src.utils.time_utils import utc_now_iso


class LegacyJsonImportService:
    def __init__(self, app_config, course_repository, group_repository, job_repository):
        self.app_config = app_config
        self.course_repository = course_repository
        self.group_repository = group_repository
        self.job_repository = job_repository

    def import_if_needed(self) -> None:
        self._import_courses()
        self._import_groups()
        self._import_history()

    def _import_courses(self) -> None:
        if not self.course_repository.is_empty():
            return
        for item in self._read_list(self.app_config.registered_courses_file):
            try:
                self.course_repository.upsert_course(item)
            except Exception:
                continue

    def _import_groups(self) -> None:
        if not self.group_repository.is_empty():
            return
        for item in self._read_list(self.app_config.groups_file):
            try:
                created = self.group_repository.create_group(
                    item.get("name", ""),
                    item.get("course_refs", []),
                    item.get("description", ""),
                    item.get("notes", ""),
                )
                if item.get("is_active") is False:
                    self.group_repository.deactivate_group(created["id"])
            except Exception:
                continue

    def _import_history(self) -> None:
        if not self.job_repository.is_empty():
            return
        for item in self._read_list(self.app_config.history_file):
            try:
                snapshot = {
                    "id": item.get("id") or item.get("public_id") or "",
                    "kind": item.get("kind") or "unknown",
                    "title": item.get("title") or item.get("kind") or "Historico importado",
                    "status": item.get("status") or "completed",
                    "created_at": item.get("created_at") or utc_now_iso(),
                    "updated_at": item.get("updated_at") or item.get("created_at") or utc_now_iso(),
                    "started_at": item.get("started_at"),
                    "finished_at": item.get("finished_at"),
                    "progress": item.get("progress") or {"current": 1, "total": 1, "percent": 100, "step": "Importado"},
                    "summary": item.get("summary") or {},
                    "result": item.get("result"),
                    "error": item.get("error"),
                    "logs": item.get("logs") or [],
                    "report_filename": item.get("report_filename"),
                    "request_payload": None,
                    "base_url": "",
                    "request_token_source": "",
                    "requested_strategy": ((item.get("result") or {}).get("summary") or {}).get("requested_strategy") or "",
                    "effective_strategy": ((item.get("result") or {}).get("summary") or {}).get("effective_strategy") or "",
                    "dry_run": bool((((item.get("result") or {}).get("summary") or {}).get("dry_run"))),
                    "dedupe": bool((((item.get("result") or {}).get("summary") or {}).get("dedupe"))),
                }
                if not snapshot["id"]:
                    continue
                self.job_repository.create_job(snapshot)
                for log_entry in snapshot["logs"]:
                    self.job_repository.add_log(snapshot["id"], log_entry)
                self.job_repository.update_job(snapshot, replace_results=True)
            except Exception:
                continue

    @staticmethod
    def _read_list(path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
        return payload if isinstance(payload, list) else []
