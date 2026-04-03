from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta

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
        response = {
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
        recurrence_id = str(payload.get("recurrence_id") or "").strip()
        if recurrence_id:
            recurrence = self.recurrence_repository.get_recurrence(recurrence_id, active_only=None)
            if not recurrence:
                raise ValueError("Recorrencia de avisos nao encontrada.")
            diff = self._build_update_diff(recurrence, prepared)
            response["edit_diff"] = self._serialize_edit_diff(diff)
            response["summary"].update(
                {
                    "editing": True,
                    "added_courses": diff["added_courses"],
                    "removed_courses": diff["removed_courses"],
                    "updated_courses": diff["updated_courses"],
                    "unchanged_courses": diff["unchanged_courses"],
                    "delete_items_expected": diff["delete_items_expected"],
                    "create_items_expected": diff["create_items_expected"],
                }
            )
        return response

    def create_recurrence(self, payload: dict) -> dict:
        prepared = self._prepare(payload)
        user = prepared["user"]
        items, failure_count = self._create_canvas_items(prepared, occurrence_index_start=1)

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

    def update_recurrence(self, recurrence_id: str, payload: dict) -> dict:
        recurrence = self.recurrence_repository.get_recurrence(recurrence_id, active_only=None)
        if not recurrence:
            raise ValueError("Recorrencia de avisos nao encontrada.")

        prepared = self._prepare(payload)
        client = prepared["client"]
        diff = self._build_update_diff(recurrence, prepared)
        replace_item_ids: list[int] = []
        delete_failure_count = 0
        create_failure_count = 0
        items: list[dict] = []
        deleted_by_course = self._delete_future_items_for_courses(
            client,
            recurrence,
            diff["delete_courses"],
        )

        for course_ref, result in deleted_by_course.items():
            replace_item_ids.extend(result["deleted_item_ids"])
            delete_failure_count += result["failure_count"]

        remaining_max_occurrence_by_course = self._remaining_occurrence_max_by_course(
            recurrence,
            replace_item_ids,
        )
        courses_by_ref = {course["course_ref"]: course for course in prepared["courses"]}
        courses_to_create = diff["added_course_refs"] | {
            course_ref
            for course_ref in diff["updated_course_refs"]
            if deleted_by_course.get(course_ref, {}).get("all_deleted", False)
        }

        for course_ref in sorted(courses_to_create):
            course = courses_by_ref.get(course_ref)
            if not course:
                continue
            course_items, failures = self._create_canvas_items_for_course(
                prepared,
                course,
                occurrence_index_start=remaining_max_occurrence_by_course.get(course_ref, 0) + 1,
            )
            items.extend(course_items)
            create_failure_count += failures

        updated = self.recurrence_repository.update_recurrence(
            recurrence_id,
            payload={
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
                "canvas_user_id": prepared["user"].get("id"),
                "canvas_user_name": prepared["user"].get("name") or prepared["user"].get("short_name") or "",
                "last_error": "Parte dos avisos antigos nao pode ser removida do Canvas." if delete_failure_count else ("Houve falhas ao recriar parte dos avisos futuros." if create_failure_count else None),
            },
            replace_item_ids=replace_item_ids,
            new_items=items,
        )
        return {
            "item": updated,
            "diff": self._serialize_edit_diff(diff),
            "replaced_count": len(replace_item_ids),
            "delete_failure_count": delete_failure_count,
            "created_count": len(items) - create_failure_count,
            "create_failure_count": create_failure_count,
            "failure_count": delete_failure_count + create_failure_count,
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
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @staticmethod
    def _render_template(template: str, **context: str | None) -> str:
        rendered = str(template or "")
        for key, value in context.items():
            rendered = re.sub(r"{{\s*" + re.escape(key) + r"\s*}}", str(value or ""), rendered)
        return rendered

    def _create_canvas_items(self, prepared: dict, *, occurrence_index_start: int) -> tuple[list[dict], int]:
        items = []
        failure_count = 0

        for course in prepared["courses"]:
            course_items, failures = self._create_canvas_items_for_course(
                prepared,
                course,
                occurrence_index_start=occurrence_index_start,
            )
            items.extend(course_items)
            failure_count += failures
        return items, failure_count

    def _create_canvas_items_for_course(self, prepared: dict, course: dict, *, occurrence_index_start: int) -> tuple[list[dict], int]:
        client = prepared["client"]
        items = []
        failure_count = 0
        for schedule_offset, publish_at in enumerate(prepared["schedule"]):
            occurrence_index = occurrence_index_start + schedule_offset
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
        return items, failure_count

    def _build_update_diff(self, recurrence: dict, prepared: dict) -> dict:
        now = utc_now()
        future_items = [
            item
            for item in recurrence.get("items", [])
            if (scheduled_for := self._parse_iso(item.get("scheduled_for")))
            and scheduled_for >= now
            and item.get("status") not in {"canceled"}
        ]
        future_by_course: dict[str, list[dict]] = {}
        for item in future_items:
            future_by_course.setdefault(str(item.get("course_ref") or ""), []).append(item)

        current_course_refs = set(future_by_course.keys())
        new_course_refs = {course["course_ref"] for course in prepared["courses"]}
        recurrence_first_publish_at = self._as_utc(self._parse_iso(recurrence.get("first_publish_at")))
        prepared_first_publish_at = self._as_utc(prepared["schedule"][0])
        content_changed = any(
            [
                str(recurrence.get("title") or "") != prepared["title"],
                str(recurrence.get("message_html") or "") != prepared["message_html"],
                bool(recurrence.get("lock_comment")) != prepared["lock_comment"],
                str(recurrence.get("recurrence_type") or "") != prepared["recurrence_type"],
                int(recurrence.get("interval_value") or 1) != prepared["interval_value"],
                int(recurrence.get("occurrence_count") or 1) != prepared["occurrence_count"],
                recurrence_first_publish_at != prepared_first_publish_at,
            ]
        )

        added_course_refs = new_course_refs - current_course_refs
        removed_course_refs = current_course_refs - new_course_refs
        kept_course_refs = current_course_refs & new_course_refs
        updated_course_refs = kept_course_refs if content_changed else set()
        unchanged_course_refs = kept_course_refs - updated_course_refs

        course_name_lookup = {
            str(item.get("course_ref") or item.get("course_id") or ""): item.get("course_name") or item.get("course_name_snapshot") or str(item.get("course_ref") or item.get("course_id") or "")
            for item in recurrence.get("items", [])
        }
        for course in prepared["courses"]:
            course_name_lookup[course["course_ref"]] = course["course_name"]

        delete_courses = removed_course_refs | updated_course_refs
        create_courses = added_course_refs | updated_course_refs
        delete_items_expected = sum(len(future_by_course.get(course_ref, [])) for course_ref in delete_courses)
        create_items_expected = len(prepared["schedule"]) * len(create_courses)

        course_changes = []
        for course_ref in sorted(new_course_refs | current_course_refs):
            if course_ref in added_course_refs:
                action = "add"
            elif course_ref in removed_course_refs:
                action = "remove"
            elif course_ref in updated_course_refs:
                action = "update"
            else:
                action = "keep"
            course_changes.append(
                {
                    "course_ref": course_ref,
                    "course_name": course_name_lookup.get(course_ref) or course_ref,
                    "action": action,
                    "future_items": len(future_by_course.get(course_ref, [])),
                    "new_occurrences": len(prepared["schedule"]) if course_ref in create_courses else 0,
                }
            )

        return {
            "content_changed": content_changed,
            "added_courses": len(added_course_refs),
            "removed_courses": len(removed_course_refs),
            "updated_courses": len(updated_course_refs),
            "unchanged_courses": len(unchanged_course_refs),
            "added_course_refs": added_course_refs,
            "removed_course_refs": removed_course_refs,
            "updated_course_refs": updated_course_refs,
            "unchanged_course_refs": unchanged_course_refs,
            "delete_courses": delete_courses,
            "create_courses": create_courses,
            "delete_items_expected": delete_items_expected,
            "create_items_expected": create_items_expected,
            "course_changes": course_changes,
        }

    def _delete_future_items_for_courses(self, client, recurrence: dict, course_refs: set[str]) -> dict[str, dict]:
        now = utc_now()
        results: dict[str, dict] = {}
        if not course_refs:
            return results
        for course_ref in course_refs:
            future_items = [
                item
                for item in recurrence.get("items", [])
                if str(item.get("course_ref") or "") == course_ref
                and (scheduled_for := self._parse_iso(item.get("scheduled_for")))
                and scheduled_for >= now
                and item.get("status") not in {"canceled"}
            ]
            deleted_item_ids: list[int] = []
            failure_count = 0
            for item in future_items:
                canvas_topic_id = item.get("canvas_topic_id")
                if canvas_topic_id:
                    try:
                        client.delete_discussion_topic(
                            course_ref=str(item.get("course_id") or item.get("course_ref")),
                            topic_id=canvas_topic_id,
                        )
                    except CanvasApiError:
                        failure_count += 1
                        continue
                deleted_item_ids.append(int(item["item_id"]))
            results[course_ref] = {
                "deleted_item_ids": deleted_item_ids,
                "failure_count": failure_count,
                "all_deleted": len(deleted_item_ids) == len(future_items),
                "future_items": len(future_items),
            }
        return results

    def _remaining_occurrence_max_by_course(self, recurrence: dict, replace_item_ids: list[int]) -> dict[str, int]:
        replaced = {int(item_id) for item_id in replace_item_ids}
        result: dict[str, int] = {}
        for item in recurrence.get("items", []):
            item_id = int(item.get("item_id") or 0)
            if item_id in replaced:
                continue
            course_ref = str(item.get("course_ref") or "")
            result[course_ref] = max(result.get(course_ref, 0), int(item.get("occurrence_index") or 0))
        return result

    @staticmethod
    def _serialize_edit_diff(diff: dict) -> dict:
        return {
            "content_changed": diff["content_changed"],
            "added_courses": diff["added_courses"],
            "removed_courses": diff["removed_courses"],
            "updated_courses": diff["updated_courses"],
            "unchanged_courses": diff["unchanged_courses"],
            "added_course_refs": sorted(diff["added_course_refs"]),
            "removed_course_refs": sorted(diff["removed_course_refs"]),
            "updated_course_refs": sorted(diff["updated_course_refs"]),
            "unchanged_course_refs": sorted(diff["unchanged_course_refs"]),
            "delete_items_expected": diff["delete_items_expected"],
            "create_items_expected": diff["create_items_expected"],
            "course_changes": diff["course_changes"],
        }
