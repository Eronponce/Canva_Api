from __future__ import annotations

import json
import logging
import threading
from uuid import uuid4

from src.utils.time_utils import utc_now_iso


LOGGER = logging.getLogger(__name__)


class JobManager:
    def __init__(self, job_repository, *, history_limit: int = 25):
        self.job_repository = job_repository
        self.history_limit = history_limit
        self._lock = threading.RLock()
        self._jobs: dict[str, dict] = {}

    @staticmethod
    def _deep_copy(job: dict | None) -> dict | None:
        if job is None:
            return None
        return json.loads(json.dumps(job))

    def create_job(
        self,
        *,
        kind: str,
        title: str,
        summary: dict | None = None,
        base_url: str = "",
        request_payload: dict | None = None,
        request_token_source: str = "",
        requested_strategy: str = "",
        effective_strategy: str = "",
        dry_run: bool = False,
        dedupe: bool = False,
        canvas_user_id: int | None = None,
        canvas_user_name: str = "",
    ) -> dict:
        job_id = uuid4().hex[:12]
        now = utc_now_iso()
        job = {
            "id": job_id,
            "kind": kind,
            "title": title,
            "status": "queued",
            "created_at": now,
            "updated_at": now,
            "started_at": None,
            "finished_at": None,
            "progress": {
                "current": 0,
                "total": 1,
                "percent": 0,
                "step": "Na fila",
            },
            "summary": summary or {},
            "result": None,
            "error": None,
            "logs": [],
            "report_filename": None,
            "base_url": base_url,
            "request_payload": request_payload,
            "request_token_source": request_token_source,
            "requested_strategy": requested_strategy,
            "effective_strategy": effective_strategy,
            "dry_run": dry_run,
            "dedupe": dedupe,
            "canvas_user_id": canvas_user_id,
            "canvas_user_name": canvas_user_name,
        }
        with self._lock:
            self._jobs[job_id] = job
        self.job_repository.create_job(job)
        return self._deep_copy(job)

    def start_background(self, job_id: str, target, *args, **kwargs) -> None:
        thread = threading.Thread(
            target=self._run_wrapper,
            args=(job_id, target, args, kwargs),
            daemon=True,
        )
        thread.start()

    def _run_wrapper(self, job_id: str, target, args, kwargs) -> None:
        try:
            target(job_id, *args, **kwargs)
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Job %s falhou com erro nao tratado.", job_id)
            self.fail(job_id, str(exc))

    def get_job(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                return self._deep_copy(job)
        return self._deep_copy(self.job_repository.get_job(job_id))

    def list_history(self) -> list[dict]:
        return self.job_repository.list_jobs(limit=self.history_limit)

    def mark_running(self, job_id: str, *, total: int, step: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            now = utc_now_iso()
            job["status"] = "running"
            job["updated_at"] = now
            job["started_at"] = job["started_at"] or now
            job["progress"] = {
                "current": 0,
                "total": max(total, 1),
                "percent": 0,
                "step": step,
            }
            snapshot = self._deep_copy(job)
        self.job_repository.update_job(snapshot)

    def set_progress(
        self,
        job_id: str,
        *,
        current: int | None = None,
        total: int | None = None,
        step: str | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs[job_id]
            progress = job["progress"]
            if current is not None:
                progress["current"] = current
            if total is not None:
                progress["total"] = max(total, 1)
            if step is not None:
                progress["step"] = step
            progress["percent"] = int((progress["current"] / progress["total"]) * 100)
            job["updated_at"] = utc_now_iso()
            snapshot = self._deep_copy(job)
        self.job_repository.update_job(snapshot)

    def update_metadata(self, job_id: str, **updates) -> None:
        allowed_keys = {
            "base_url",
            "request_payload",
            "request_token_source",
            "requested_strategy",
            "effective_strategy",
            "dry_run",
            "dedupe",
            "canvas_user_id",
            "canvas_user_name",
            "summary",
            "result",
            "report_filename",
            "error",
        }
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            for key, value in updates.items():
                if key in allowed_keys:
                    job[key] = value
            job["updated_at"] = utc_now_iso()
            snapshot = self._deep_copy(job)
        self.job_repository.update_job(snapshot)

    def add_log(self, job_id: str, *, level: str, message: str, data: dict | None = None) -> None:
        log_entry = {
            "timestamp": utc_now_iso(),
            "level": level.upper(),
            "message": message,
            "data": data or {},
        }
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job["logs"].append(log_entry)
                job["updated_at"] = log_entry["timestamp"]
        self.job_repository.add_log(job_id, log_entry)
        LOGGER.info("job=%s level=%s message=%s data=%s", job_id, level.upper(), message, data or {})

    def complete(self, job_id: str, *, result: dict, report_filename: str | None = None) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = "completed"
            job["updated_at"] = utc_now_iso()
            job["finished_at"] = job["updated_at"]
            job["progress"]["current"] = job["progress"]["total"]
            job["progress"]["percent"] = 100
            job["progress"]["step"] = "Concluido"
            job["result"] = result
            job["report_filename"] = report_filename
            snapshot = self._deep_copy(job)

        self.job_repository.update_job(snapshot, replace_results=True)
        with self._lock:
            self._jobs.pop(job_id, None)

    def fail(self, job_id: str, error_message: str, *, result: dict | None = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                job = self.job_repository.get_job(job_id)
                if job is None:
                    return
                self._jobs[job_id] = job

            job["status"] = "failed"
            job["updated_at"] = utc_now_iso()
            job["finished_at"] = job["updated_at"]
            job["progress"]["step"] = "Falhou"
            job["error"] = error_message
            job["result"] = result
            snapshot = self._deep_copy(job)

        self.job_repository.update_job(snapshot, replace_results=True)
        with self._lock:
            self._jobs.pop(job_id, None)
