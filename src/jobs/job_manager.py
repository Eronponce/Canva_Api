from __future__ import annotations

import json
import logging
import threading
from uuid import uuid4

from src.utils.time_utils import utc_now_iso


LOGGER = logging.getLogger(__name__)


class JobManager:
    def __init__(self, history_store):
        self.history_store = history_store
        self._lock = threading.RLock()
        self._jobs: dict[str, dict] = {}

    def _deep_copy(self, job: dict) -> dict:
        return json.loads(json.dumps(job))

    def create_job(self, *, kind: str, title: str, summary: dict | None = None) -> dict:
        job_id = uuid4().hex[:12]
        now = utc_now_iso()
        job = {
            "id": job_id,
            "kind": kind,
            "title": title,
            "status": "queued",
            "created_at": now,
            "updated_at": now,
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
        }
        with self._lock:
            self._jobs[job_id] = job
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
            LOGGER.exception("Job %s falhou com erro não tratado.", job_id)
            self.fail(job_id, str(exc))

    def get_job(self, job_id: str) -> dict | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                return self._deep_copy(job)
        history_entry = self.history_store.get_entry(job_id)
        return self._deep_copy(history_entry) if history_entry else None

    def list_history(self) -> list[dict]:
        return self.history_store.list_entries()

    def mark_running(self, job_id: str, *, total: int, step: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = "running"
            job["updated_at"] = utc_now_iso()
            job["progress"] = {
                "current": 0,
                "total": max(total, 1),
                "percent": 0,
                "step": step,
            }

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

    def add_log(self, job_id: str, *, level: str, message: str, data: dict | None = None) -> None:
        log_entry = {
            "timestamp": utc_now_iso(),
            "level": level.upper(),
            "message": message,
            "data": data or {},
        }
        with self._lock:
            job = self._jobs[job_id]
            job["logs"].append(log_entry)
            job["updated_at"] = log_entry["timestamp"]
        LOGGER.info("job=%s level=%s message=%s data=%s", job_id, level.upper(), message, data or {})

    def complete(self, job_id: str, *, result: dict, report_filename: str | None = None) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = "completed"
            job["updated_at"] = utc_now_iso()
            job["finished_at"] = job["updated_at"]
            job["progress"]["current"] = job["progress"]["total"]
            job["progress"]["percent"] = 100
            job["progress"]["step"] = "Concluído"
            job["result"] = result
            job["report_filename"] = report_filename
            snapshot = self._deep_copy(job)

        self.history_store.append_entry(snapshot)

    def fail(self, job_id: str, error_message: str, *, result: dict | None = None) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job["status"] = "failed"
            job["updated_at"] = utc_now_iso()
            job["finished_at"] = job["updated_at"]
            job["progress"]["step"] = "Falhou"
            job["error"] = error_message
            job["result"] = result
            snapshot = self._deep_copy(job)

        self.history_store.append_entry(snapshot)
