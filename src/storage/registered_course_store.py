from __future__ import annotations

from src.storage.json_store import JsonFileStore
from src.utils.time_utils import utc_now_iso


class RegisteredCourseStore:
    def __init__(self, courses_file):
        self.store = JsonFileStore(courses_file, list)

    def list_courses(self) -> list[dict]:
        courses = self.store.read() or []
        normalized = [self._normalize_item(item) for item in courses]
        return sorted(
            normalized,
            key=lambda item: (
                (item.get("course_name") or "").lower(),
                item.get("course_ref", ""),
            ),
        )

    def add_course(self, course_payload: dict | str) -> dict:
        payload = self._build_payload(course_payload)
        existing = self.list_courses()

        if any(item.get("course_ref") == payload["course_ref"] for item in existing):
            raise ValueError("Esse curso ja foi cadastrado.")

        def updater(courses):
            courses.append(payload)
            return courses

        self.store.update(updater)
        return payload

    def delete_course(self, course_ref: str) -> bool:
        removed = False
        normalized = str(course_ref or "").strip()

        def updater(courses):
            nonlocal removed
            filtered = [item for item in courses if str(item.get("course_ref", "")).strip() != normalized]
            removed = len(filtered) != len(courses)
            return filtered

        self.store.update(updater)
        return removed

    def _build_payload(self, course_payload: dict | str) -> dict:
        if isinstance(course_payload, str):
            course_ref = course_payload
            payload = {}
        else:
            payload = dict(course_payload or {})
            course_ref = payload.get("course_ref", "")

        cleaned_ref = str(course_ref or "").strip()
        if not cleaned_ref:
            raise ValueError("Informe o numero do curso para cadastrar.")

        timestamp = utc_now_iso()
        return {
            "course_ref": cleaned_ref,
            "canvas_course_id": payload.get("canvas_course_id"),
            "course_name": (payload.get("course_name") or "").strip(),
            "course_code": (payload.get("course_code") or "").strip(),
            "term_name": (payload.get("term_name") or "").strip(),
            "workflow_state": (payload.get("workflow_state") or "").strip(),
            "created_at": payload.get("created_at") or timestamp,
            "updated_at": payload.get("updated_at") or timestamp,
        }

    def _normalize_item(self, item: dict) -> dict:
        payload = self._build_payload(item)
        payload["created_at"] = item.get("created_at") or payload["created_at"]
        payload["updated_at"] = item.get("updated_at") or payload["updated_at"]
        return payload
