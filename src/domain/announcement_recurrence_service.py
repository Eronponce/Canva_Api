from __future__ import annotations

from datetime import datetime, timedelta

from src.services.canvas_client import CanvasApiError
from src.utils.time_utils import datetime_to_iso, parse_schedule_datetime, utc_now


class AnnouncementRecurrenceService:
    def __init__(self, connection_service, course_service, recurrence_repository):
        self.connection_service = connection_service
        self.course_service = course_service
        self.recurrence_repository = recurrence_repository

    def list_recurrences(self, *, include_inactive: bool = False) -> dict:
        items = self.recurrence_repository.list_recurrences(active_only=None if include_inactive else True)
        return {"items": items}

    def get_recurrence(self, recurrence_id: str, *, include_inactive: bool = False) -> dict:
        item = self.recurrence_repository.get_recurrence(recurrence_id, active_only=None if include_inactive else True)
        if not item:
            raise ValueError("Recorrencia de avisos nao encontrada.")
        return {"item": item}

    def preview(self, payload: dict) -> dict:
        prepared = self._prepare(payload)
        return {
            "summary": {
                "courses": len(prepared["courses"]),
                "occurrences_per_course": len(prepared["schedule"]),
                "total_announcements": len(prepared["courses"]) * len(prepared["schedule"]),
                "recurrence_type": prepared["recurrence_type"],
                "interval_value": prepared["interval_value"],
                "first_publish_at": datetime_to_iso(prepared["schedule"][0]),
                "last_publish_at": datetime_to_iso(prepared["schedule"][-1]),
            },
            "courses": prepared["courses"],
            "schedule": [
                {
                    "occurrence_index": index,
                    "publish_at": datetime_to_iso(when),
                }
                for index, when in enumerate(prepared["schedule"], start=1)
            ],
        }

    def create_recurrence(self, payload: dict) -> dict:
        prepared = self._prepare(payload)
        client = prepared["client"]
        user = prepared["user"]
        items = []
        failure_count = 0

        for course in prepared["courses"]:
            for occurrence_index, publish_at in enumerate(prepared["schedule"], start=1):
                try:
                    rendered_title = self._render_template(
                        prepared["title"],
                        course_name=course["course_name"],
                        course_ref=course["course_ref"],
                        course_code=course.get("course_code"),
                    )
                    rendered_message_html = self._render_template(
                        prepared["message_html"],
                        course_name=course["course_name"],
                        course_ref=course["course_ref"],
                        course_code=course.get("course_code"),
                    )
                    response = client.create_announcement(
                        course_ref=str(course["course_id"]),
                        title=rendered_title,
                        message_html=rendered_message_html,
                        published=True,
                        delayed_post_at=publish_at.isoformat(),
                        lock_comment=prepared["lock_comment"],
                    )
                    items.append(
                        {
                            "occurrence_index": occurrence_index,
                            "course_ref_snapshot": course["course_ref"],
                            "course_id_snapshot": course["course_id"],
                            "course_name_snapshot": course["course_name"],
                            "scheduled_for": publish_at,
                            "canvas_topic_id": response.get("id"),
                            "canvas_topic_url": response.get("html_url"),
                            "status": "scheduled",
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    failure_count += 1
                    items.append(
                        {
                            "occurrence_index": occurrence_index,
                            "course_ref_snapshot": course["course_ref"],
                            "course_id_snapshot": course["course_id"],
                            "course_name_snapshot": course["course_name"],
                            "scheduled_for": publish_at,
                            "status": "error",
                            "error_message": str(exc),
                        }
                    )

        record = self.recurrence_repository.create_recurrence(
            {
                "name": prepared["name"],
                "title": prepared["title"],
                "message_html": prepared["message_html"],
                "lock_comment": prepared["lock_comment"],
                "target_mode": prepared["target_mode"],
                "target_config_json": prepared["target_config_json"],
                "recurrence_type": prepared["recurrence_type"],
                "interval_value": prepared["interval_value"],
                "occurrence_count": prepared["occurrence_count"],
                "first_publish_at": prepared["schedule"][0],
                "client_timezone": prepared["client_timezone"],
                "base_url_snapshot": prepared["base_url"],
                "canvas_user_id": user.get("id"),
                "canvas_user_name": user.get("name") or user.get("short_name") or "",
                "last_error": "Houve falhas ao criar parte dos avisos agendados." if failure_count else None,
            },
            items,
        )
        return {
            "item": record,
            "created_count": len(items) - failure_count,
            "failure_count": failure_count,
        }

    def cancel_recurrence(self, recurrence_id: str, payload: dict) -> dict:
        recurrence = self.recurrence_repository.get_recurrence(recurrence_id, active_only=None)
        if not recurrence:
            raise ValueError("Recorrencia de avisos nao encontrada.")

        client = self.connection_service.build_client(payload)
        now = utc_now()
        item_updates = []
        canceled_count = 0
        failure_count = 0
        skipped_count = 0

        for item in recurrence["items"]:
            scheduled_for = self._parse_iso(item.get("scheduled_for"))
            if not scheduled_for or scheduled_for < now:
                skipped_count += 1
                continue
            if item.get("status") == "canceled":
                skipped_count += 1
                continue
            if not item.get("canvas_topic_id"):
                item_updates.append(
                    {
                        "item_id": item["item_id"],
                        "status": "canceled",
                        "deleted_on_canvas": False,
                        "canceled_at": now,
                        "error_message": item.get("error_message"),
                    }
                )
                skipped_count += 1
                continue

            try:
                client.delete_discussion_topic(
                    course_ref=str(item.get("course_id") or item.get("course_ref")),
                    topic_id=item["canvas_topic_id"],
                )
                item_updates.append(
                    {
                        "item_id": item["item_id"],
                        "status": "canceled",
                        "deleted_on_canvas": True,
                        "canceled_at": now,
                        "error_message": None,
                    }
                )
                canceled_count += 1
            except CanvasApiError as exc:
                item_updates.append(
                    {
                        "item_id": item["item_id"],
                        "status": "error",
                        "deleted_on_canvas": False,
                        "canceled_at": now,
                        "error_message": exc.message,
                    }
                )
                failure_count += 1

        updated = self.recurrence_repository.cancel_recurrence(
            recurrence_id,
            cancel_reason=str(payload.get("cancel_reason") or "").strip(),
            item_updates=item_updates,
        )
        return {
            "item": updated,
            "canceled_count": canceled_count,
            "failure_count": failure_count,
            "skipped_count": skipped_count,
        }

    def _prepare(self, payload: dict) -> dict:
        course_refs = self.course_service.resolve_payload_course_refs(payload)
        if not course_refs:
            raise ValueError("Selecione ao menos um grupo ou curso para criar a recorrencia.")

        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("Informe o titulo do aviso recorrente.")

        message_html = str(payload.get("message_html") or "").strip()
        if not message_html:
            raise ValueError("Informe a mensagem HTML do aviso recorrente.")

        recurrence_type = str(payload.get("recurrence_type") or "weekly").strip().lower()
        if recurrence_type not in {"daily", "weekly"}:
            raise ValueError("A recorrencia de avisos aceita apenas frequencia diaria ou semanal.")

        interval_value = max(int(payload.get("interval_value") or 1), 1)
        occurrence_count = max(int(payload.get("occurrence_count") or 1), 1)
        if occurrence_count > 120:
            raise ValueError("Use no maximo 120 ocorrencias por recorrencia.")

        client_timezone = str(payload.get("client_timezone") or "UTC").strip() or "UTC"
        first_publish_raw = str(payload.get("first_publish_at_local") or "").strip()
        first_publish_iso = parse_schedule_datetime(first_publish_raw, client_timezone)
        if not first_publish_iso:
            raise ValueError("Informe a data e hora da primeira publicacao.")

        first_publish_at = datetime.fromisoformat(first_publish_iso.replace("Z", "+00:00"))
        if first_publish_at < utc_now():
            raise ValueError("A primeira publicacao precisa estar no futuro.")

        total_posts = len(course_refs) * occurrence_count
        if total_posts > 1000:
            raise ValueError("Essa recorrencia geraria mais de 1000 avisos. Reduza cursos ou ocorrencias.")

        client = self.connection_service.build_client(payload)
        user = client.get_current_user()
        courses = []
        for course_ref in course_refs:
            course = client.get_course(course_ref)
            courses.append(
                {
                    "course_ref": str(course_ref),
                    "course_id": course.get("id"),
                    "course_name": course.get("name") or str(course_ref),
                    "course_code": course.get("course_code") or "",
                }
            )

        schedule = self._build_schedule(
            first_publish_at=first_publish_at,
            recurrence_type=recurrence_type,
            interval_value=interval_value,
            occurrence_count=occurrence_count,
        )
        name = str(payload.get("name") or "").strip() or title

        return {
            "client": client,
            "user": user,
            "courses": courses,
            "schedule": schedule,
            "name": name,
            "title": title,
            "message_html": message_html,
            "lock_comment": bool(payload.get("lock_comment")),
            "target_mode": "courses" if str(payload.get("target_mode") or "").strip() == "courses" else "groups",
            "target_config_json": {
                "group_ids": [str(item).strip() for item in (payload.get("group_ids") or []) if str(item).strip()],
                "course_refs": course_refs,
                "select_all_groups": bool(payload.get("select_all_groups")),
            },
            "recurrence_type": recurrence_type,
            "interval_value": interval_value,
            "occurrence_count": occurrence_count,
            "client_timezone": client_timezone,
            "base_url": self.connection_service.resolve_credentials(payload)["base_url"],
        }

    @staticmethod
    def _build_schedule(*, first_publish_at: datetime, recurrence_type: str, interval_value: int, occurrence_count: int) -> list[datetime]:
        schedule = []
        for index in range(occurrence_count):
            if recurrence_type == "daily":
                schedule.append(first_publish_at + timedelta(days=index * interval_value))
            else:
                schedule.append(first_publish_at + timedelta(weeks=index * interval_value))
        return schedule

    @staticmethod
    def _parse_iso(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))

    @staticmethod
    def _render_template(template: str, **context: str | None) -> str:
        rendered = str(template or "")
        for key, value in context.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value or ""))
        return rendered
