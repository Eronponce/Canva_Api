from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import delete, inspect, select, text, update
from sqlalchemy.orm import selectinload

from src.database.models import (
    AnnouncementRecurrence,
    AnnouncementRecurrenceItem,
    Course,
    CourseGroup,
    GroupCourse,
    JobCourseResult,
    JobLog,
    JobRun,
    JobTargetCourse,
    JobTargetGroup,
)
from src.utils.time_utils import datetime_to_iso, utc_now


def _soft_delete_fields(*, active: bool) -> dict:
    now = utc_now()
    if active:
        return {
            "is_active": True,
            "is_deleted": False,
            "activated_at": now,
            "deactivated_at": None,
            "deleted_at": None,
            "updated_at": now,
        }
    return {
        "is_active": False,
        "is_deleted": True,
        "deactivated_at": now,
        "deleted_at": now,
        "updated_at": now,
    }


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _with_timezone(value: datetime | None, timezone_name: str | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        try:
            return value.replace(tzinfo=ZoneInfo(timezone_name or "UTC"))
        except Exception:  # noqa: BLE001
            return value.replace(tzinfo=UTC)
    if timezone_name:
        try:
            return value.astimezone(ZoneInfo(timezone_name))
        except Exception:  # noqa: BLE001
            return value
    return value


def _short_course_code(course_code: str | None) -> str:
    normalized = str(course_code or "").strip()
    if not normalized:
        return ""
    return normalized.split("@", 1)[0].strip() or normalized


class CourseRepository:
    def __init__(self, database):
        self.database = database

    def is_empty(self) -> bool:
        with self.database.session_scope() as session:
            return session.scalar(select(Course.id).limit(1)) is None

    def list_courses(self, *, active_only: bool | None = None) -> list[dict]:
        with self.database.session_scope() as session:
            stmt = select(Course).order_by(Course.course_name.asc(), Course.course_ref.asc())
            if active_only is True:
                stmt = stmt.where(Course.is_active.is_(True), Course.is_deleted.is_(False))
            elif active_only is False:
                stmt = stmt.where(Course.is_active.is_(False))
            rows = session.scalars(stmt).all()
            return [self._serialize_course(item) for item in rows]

    def get_course_by_ref(self, course_ref: str, *, active_only: bool | None = None) -> dict | None:
        normalized = str(course_ref or "").strip()
        if not normalized:
            return None
        with self.database.session_scope() as session:
            stmt = select(Course).where(Course.course_ref == normalized)
            if active_only is True:
                stmt = stmt.where(Course.is_active.is_(True), Course.is_deleted.is_(False))
            row = session.scalar(stmt)
            return self._serialize_course(row) if row else None

    def upsert_course(self, payload: dict) -> dict:
        normalized_ref = str(payload.get("course_ref") or "").strip()
        if not normalized_ref:
            raise ValueError("Informe o numero do curso para cadastrar.")

        now = utc_now()
        with self.database.session_scope() as session:
            row = session.scalar(select(Course).where(Course.course_ref == normalized_ref))
            if row is None:
                row = Course(
                    course_ref=normalized_ref,
                    created_at=now,
                    updated_at=now,
                    activated_at=now,
                )
                session.add(row)

            row.canvas_course_id = payload.get("canvas_course_id")
            row.course_name = (payload.get("course_name") or "").strip()
            row.course_code = (payload.get("course_code") or "").strip()
            row.term_name = (payload.get("term_name") or "").strip()
            row.workflow_state = (payload.get("workflow_state") or "").strip()
            row.source_type = (payload.get("source_type") or "manual").strip() or "manual"
            row.notes = (payload.get("notes") or "").strip()
            row.metadata_json = payload.get("metadata_json")
            row.last_synced_at = now
            row.updated_at = now
            row.is_active = True
            row.is_deleted = False
            row.activated_at = now
            row.deactivated_at = None
            row.deleted_at = None
            session.flush()
            return self._serialize_course(row)

    def deactivate_course(self, course_ref: str) -> bool:
        return self._set_course_active(course_ref, active=False)

    def delete_course(self, course_ref: str) -> bool:
        normalized = str(course_ref or "").strip()
        if not normalized:
            return False
        with self.database.session_scope() as session:
            row = session.scalar(select(Course).where(Course.course_ref == normalized))
            if row is None:
                return False

            session.execute(
                update(JobTargetCourse)
                .where(JobTargetCourse.course_id == row.id)
                .values(course_id=None)
            )
            session.execute(
                update(JobCourseResult)
                .where(JobCourseResult.course_id == row.id)
                .values(course_id=None)
            )
            session.execute(delete(GroupCourse).where(GroupCourse.course_id == row.id))
            session.delete(row)
            return True

    def reactivate_course(self, course_ref: str) -> dict | None:
        changed = self._set_course_active(course_ref, active=True)
        if not changed:
            return None
        return self.get_course_by_ref(course_ref)

    def _set_course_active(self, course_ref: str, *, active: bool) -> bool:
        normalized = str(course_ref or "").strip()
        with self.database.session_scope() as session:
            row = session.scalar(select(Course).where(Course.course_ref == normalized))
            if row is None:
                return False
            for key, value in _soft_delete_fields(active=active).items():
                setattr(row, key, value)
            return True

    @staticmethod
    def _serialize_course(row: Course) -> dict:
        return {
            "course_ref": row.course_ref,
            "canvas_course_id": row.canvas_course_id,
            "course_name": row.course_name,
            "course_code": row.course_code,
            "course_code_short": _short_course_code(row.course_code),
            "term_name": row.term_name,
            "workflow_state": row.workflow_state,
            "source_type": row.source_type,
            "notes": row.notes,
            "metadata_json": row.metadata_json,
            "is_active": row.is_active,
            "is_deleted": row.is_deleted,
            "created_at": datetime_to_iso(row.created_at),
            "updated_at": datetime_to_iso(row.updated_at),
            "activated_at": datetime_to_iso(row.activated_at),
            "deactivated_at": datetime_to_iso(row.deactivated_at),
            "deleted_at": datetime_to_iso(row.deleted_at),
            "last_synced_at": datetime_to_iso(row.last_synced_at),
        }


class GroupRepository:
    def __init__(self, database):
        self.database = database

    def is_empty(self) -> bool:
        with self.database.session_scope() as session:
            return session.scalar(select(CourseGroup.id).limit(1)) is None

    def list_groups(self, *, active_only: bool | None = None) -> list[dict]:
        with self.database.session_scope() as session:
            stmt = (
                select(CourseGroup)
                .options(selectinload(CourseGroup.course_links).selectinload(GroupCourse.course))
                .order_by(CourseGroup.name.asc(), CourseGroup.updated_at.desc())
            )
            if active_only is True:
                stmt = stmt.where(CourseGroup.is_active.is_(True), CourseGroup.is_deleted.is_(False))
            elif active_only is False:
                stmt = stmt.where(CourseGroup.is_active.is_(False))
            rows = session.scalars(stmt).all()
            return [self._serialize_group(item) for item in rows]

    def list_group_public_ids(self, *, active_only: bool = True) -> list[str]:
        return [item["id"] for item in self.list_groups(active_only=active_only)]

    def get_group(self, group_public_id: str, *, active_only: bool | None = None) -> dict | None:
        with self.database.session_scope() as session:
            stmt = (
                select(CourseGroup)
                .options(selectinload(CourseGroup.course_links).selectinload(GroupCourse.course))
                .where(CourseGroup.public_id == str(group_public_id or "").strip())
            )
            if active_only is True:
                stmt = stmt.where(CourseGroup.is_active.is_(True), CourseGroup.is_deleted.is_(False))
            row = session.scalar(stmt)
            return self._serialize_group(row) if row else None

    def create_group(self, name: str, course_refs: list[str], description: str = "", notes: str = "") -> dict:
        cleaned_name = name.strip()
        cleaned_description = description.strip()
        cleaned_notes = notes.strip()
        if not cleaned_name:
            raise ValueError("Informe um nome para o grupo de turmas.")
        if not course_refs:
            raise ValueError("Informe ao menos uma turma para salvar o grupo.")

        now = utc_now()
        with self.database.session_scope() as session:
            existing = session.scalar(select(CourseGroup).where(CourseGroup.name == cleaned_name))
            if existing and existing.is_active:
                raise ValueError("Ja existe um grupo com esse nome. Use editar para atualizar.")
            if existing and not existing.is_active:
                group = existing
                group.description = cleaned_description
                group.notes = cleaned_notes
                for key, value in _soft_delete_fields(active=True).items():
                    setattr(group, key, value)
            else:
                group = CourseGroup(
                    public_id=uuid4().hex[:12],
                    name=cleaned_name,
                    description=cleaned_description,
                    notes=cleaned_notes,
                    created_at=now,
                    updated_at=now,
                    activated_at=now,
                )
                session.add(group)
                session.flush()

            self._replace_group_courses(session, group, course_refs)
            session.flush()
            session.refresh(group)
            return self._serialize_group(group)

    def update_group(self, group_public_id: str, name: str, course_refs: list[str], description: str = "", notes: str = "") -> dict:
        cleaned_name = name.strip()
        cleaned_description = description.strip()
        cleaned_notes = notes.strip()
        if not cleaned_name:
            raise ValueError("Informe um nome para o grupo de turmas.")
        if not course_refs:
            raise ValueError("Informe ao menos uma turma para salvar o grupo.")

        now = utc_now()
        with self.database.session_scope() as session:
            group = session.scalar(
                select(CourseGroup)
                .options(selectinload(CourseGroup.course_links).selectinload(GroupCourse.course))
                .where(CourseGroup.public_id == str(group_public_id or "").strip())
            )
            if group is None:
                raise ValueError("Grupo nao encontrado.")

            duplicate = session.scalar(
                select(CourseGroup)
                .where(CourseGroup.name == cleaned_name, CourseGroup.public_id != group.public_id)
            )
            if duplicate and duplicate.is_active:
                raise ValueError("Ja existe outro grupo com esse nome.")

            group.name = cleaned_name
            group.description = cleaned_description
            group.notes = cleaned_notes
            group.updated_at = now
            self._replace_group_courses(session, group, course_refs)
            session.flush()
            session.refresh(group)
            return self._serialize_group(group)

    def deactivate_group(self, group_public_id: str) -> bool:
        with self.database.session_scope() as session:
            group = session.scalar(select(CourseGroup).where(CourseGroup.public_id == str(group_public_id or "").strip()))
            if group is None:
                return False
            for key, value in _soft_delete_fields(active=False).items():
                setattr(group, key, value)
            return True

    def delete_group(self, group_public_id: str) -> bool:
        normalized = str(group_public_id or "").strip()
        if not normalized:
            return False
        with self.database.session_scope() as session:
            group = session.scalar(select(CourseGroup).where(CourseGroup.public_id == normalized))
            if group is None:
                return False

            session.execute(
                update(JobTargetGroup)
                .where(JobTargetGroup.group_id == group.id)
                .values(group_id=None)
            )
            session.execute(delete(GroupCourse).where(GroupCourse.group_id == group.id))
            session.delete(group)
            return True

    def reactivate_group(self, group_public_id: str) -> dict | None:
        now = utc_now()
        with self.database.session_scope() as session:
            group = session.scalar(
                select(CourseGroup)
                .options(selectinload(CourseGroup.course_links).selectinload(GroupCourse.course))
                .where(CourseGroup.public_id == str(group_public_id or "").strip())
            )
            if group is None:
                return None
            group.is_active = True
            group.is_deleted = False
            group.activated_at = now
            group.deactivated_at = None
            group.deleted_at = None
            group.updated_at = now
            session.flush()
            session.refresh(group)
            return self._serialize_group(group)

    def _replace_group_courses(self, session, group: CourseGroup, course_refs: list[str]) -> None:
        normalized_refs = [str(ref).strip() for ref in course_refs if str(ref).strip()]
        course_rows = session.scalars(select(Course).where(Course.course_ref.in_(normalized_refs))).all()
        lookup = {item.course_ref: item for item in course_rows}
        missing = [ref for ref in normalized_refs if ref not in lookup]
        if missing:
            raise ValueError("Cadastre os cursos antes de adiciona-los ao grupo.")

        current_links = {link.course.course_ref: link for link in group.course_links if link.course is not None}
        now = utc_now()
        seen = set()
        for position, course_ref in enumerate(normalized_refs):
            seen.add(course_ref)
            course_row = lookup[course_ref]
            link = current_links.get(course_ref)
            if link is None:
                link = GroupCourse(
                    group_id=group.id,
                    course_id=course_row.id,
                    position=position,
                    created_at=now,
                    updated_at=now,
                    activated_at=now,
                    added_at=now,
                    is_active=True,
                    is_deleted=False,
                )
                session.add(link)
                group.course_links.append(link)
            else:
                link.position = position
                link.course_id = course_row.id
                link.updated_at = now
                link.is_active = True
                link.is_deleted = False
                link.activated_at = now
                link.deactivated_at = None
                link.deleted_at = None
                if link.added_at is None:
                    link.added_at = now
                link.removed_at = None

        for course_ref, link in current_links.items():
            if course_ref in seen:
                continue
            link.is_active = False
            link.is_deleted = True
            link.updated_at = now
            link.deactivated_at = now
            link.deleted_at = now
            link.removed_at = now

    @staticmethod
    def _serialize_group(row: CourseGroup) -> dict:
        active_links = [
            link
            for link in sorted(row.course_links, key=lambda item: item.position)
            if link.is_active and not link.is_deleted
        ]
        courses = []
        for link in active_links:
            course = link.course
            if course is None:
                continue
            courses.append(
                {
                    "course_ref": course.course_ref,
                    "course_name": course.course_name,
                    "course_code": course.course_code,
                    "course_code_short": _short_course_code(course.course_code),
                    "term_name": course.term_name,
                    "canvas_course_id": course.canvas_course_id,
                    "workflow_state": course.workflow_state,
                    "is_active": course.is_active,
                }
            )
        return {
            "id": row.public_id,
            "name": row.name,
            "description": row.description,
            "notes": row.notes,
            "course_refs": [item["course_ref"] for item in courses],
            "courses": courses,
            "is_active": row.is_active,
            "is_deleted": row.is_deleted,
            "created_at": datetime_to_iso(row.created_at),
            "updated_at": datetime_to_iso(row.updated_at),
            "activated_at": datetime_to_iso(row.activated_at),
            "deactivated_at": datetime_to_iso(row.deactivated_at),
            "deleted_at": datetime_to_iso(row.deleted_at),
        }


class JobRepository:
    def __init__(self, database):
        self.database = database

    def is_empty(self) -> bool:
        with self.database.session_scope() as session:
            return session.scalar(select(JobRun.id).limit(1)) is None

    def create_job(self, snapshot: dict) -> None:
        with self.database.session_scope() as session:
            row = JobRun(
                public_id=snapshot["id"],
                kind=snapshot["kind"],
                title=snapshot["title"],
                status=snapshot["status"],
                base_url=snapshot.get("base_url") or "",
                request_token_source=snapshot.get("request_token_source") or "",
                request_payload_json=snapshot.get("request_payload"),
                summary_json=snapshot.get("summary") or {},
                result_json=snapshot.get("result"),
                error_message=snapshot.get("error"),
                report_filename=snapshot.get("report_filename"),
                requested_strategy=snapshot.get("requested_strategy") or "",
                effective_strategy=snapshot.get("effective_strategy") or "",
                dry_run=bool(snapshot.get("dry_run")),
                dedupe=bool(snapshot.get("dedupe")),
                progress_current=(snapshot.get("progress") or {}).get("current", 0),
                progress_total=(snapshot.get("progress") or {}).get("total", 1),
                progress_percent=(snapshot.get("progress") or {}).get("percent", 0),
                progress_step=(snapshot.get("progress") or {}).get("step", ""),
                created_at=self._from_iso(snapshot.get("created_at")) or utc_now(),
                updated_at=self._from_iso(snapshot.get("updated_at")) or utc_now(),
                started_at=self._from_iso(snapshot.get("started_at")),
                finished_at=self._from_iso(snapshot.get("finished_at")),
            )
            session.add(row)
            session.flush()
            self._sync_targets(session, row, snapshot.get("summary") or {})

    def update_job(self, snapshot: dict, *, replace_results: bool = False) -> None:
        with self.database.session_scope() as session:
            row = session.scalar(
                select(JobRun)
                .options(selectinload(JobRun.target_groups), selectinload(JobRun.target_courses), selectinload(JobRun.course_results))
                .where(JobRun.public_id == snapshot["id"])
            )
            if row is None:
                self.create_job(snapshot)
                return

            row.kind = snapshot["kind"]
            row.title = snapshot["title"]
            row.status = snapshot["status"]
            row.base_url = snapshot.get("base_url") or row.base_url
            row.request_token_source = snapshot.get("request_token_source") or row.request_token_source
            row.request_payload_json = snapshot.get("request_payload") or row.request_payload_json
            row.summary_json = snapshot.get("summary") or {}
            row.result_json = snapshot.get("result")
            row.error_message = snapshot.get("error")
            row.report_filename = snapshot.get("report_filename")
            row.requested_strategy = snapshot.get("requested_strategy") or row.requested_strategy
            row.effective_strategy = snapshot.get("effective_strategy") or row.effective_strategy
            row.dry_run = bool(snapshot.get("dry_run"))
            row.dedupe = bool(snapshot.get("dedupe"))
            row.progress_current = (snapshot.get("progress") or {}).get("current", row.progress_current)
            row.progress_total = (snapshot.get("progress") or {}).get("total", row.progress_total)
            row.progress_percent = (snapshot.get("progress") or {}).get("percent", row.progress_percent)
            row.progress_step = (snapshot.get("progress") or {}).get("step", row.progress_step)
            row.updated_at = self._from_iso(snapshot.get("updated_at")) or utc_now()
            row.started_at = self._from_iso(snapshot.get("started_at")) or row.started_at
            row.finished_at = self._from_iso(snapshot.get("finished_at")) or row.finished_at
            row.canvas_user_id = snapshot.get("canvas_user_id") or row.canvas_user_id
            row.canvas_user_name = snapshot.get("canvas_user_name") or row.canvas_user_name
            self._sync_targets(session, row, snapshot.get("summary") or {})
            if replace_results:
                self._replace_course_results(session, row, (snapshot.get("result") or {}).get("course_results", []))

    def add_log(self, job_public_id: str, log_entry: dict) -> None:
        with self.database.session_scope() as session:
            row = session.scalar(select(JobRun).where(JobRun.public_id == job_public_id))
            if row is None:
                return
            session.add(
                JobLog(
                    job_run_id=row.id,
                    level=log_entry.get("level", "INFO"),
                    message=log_entry.get("message", ""),
                    data_json=log_entry.get("data") or {},
                    created_at=self._from_iso(log_entry.get("timestamp")) or utc_now(),
                )
            )
            row.updated_at = utc_now()

    def get_job(self, job_public_id: str) -> dict | None:
        with self.database.session_scope() as session:
            row = session.scalar(
                select(JobRun)
                .options(selectinload(JobRun.logs), selectinload(JobRun.course_results))
                .where(JobRun.public_id == job_public_id)
            )
            return self._serialize_job(row, include_logs=True) if row else None

    def list_jobs(self, *, limit: int | None = None) -> list[dict]:
        with self.database.session_scope() as session:
            stmt = select(JobRun).order_by(JobRun.created_at.desc())
            if limit:
                stmt = stmt.limit(limit)
            rows = session.scalars(stmt).all()
            return [self._serialize_job(item, include_logs=False) for item in rows]

    def get_announcement_edit_target(self, *, job_public_id: str, course_ref: str, announcement_id: int | str) -> dict | None:
        normalized_job_id = str(job_public_id or "").strip()
        normalized_course_ref = str(course_ref or "").strip()
        normalized_announcement_id = str(announcement_id or "").strip()
        if not normalized_job_id or not normalized_course_ref or not normalized_announcement_id:
            return None

        with self.database.session_scope() as session:
            row = session.scalar(
                select(JobRun)
                .options(selectinload(JobRun.course_results))
                .where(JobRun.public_id == normalized_job_id)
            )
            if row is None:
                return None

            course_result = next(
                (
                    item
                    for item in row.course_results
                    if item.course_ref_snapshot == normalized_course_ref
                    and str(item.announcement_id or "") == normalized_announcement_id
                ),
                None,
            )
            if course_result is None:
                return None

            raw_result = dict(course_result.raw_result_json or {})
            return {
                "job_id": row.public_id,
                "job_kind": row.kind,
                "job_status": row.status,
                "job_title": row.title,
                "base_url": row.base_url,
                "request_payload": dict(row.request_payload_json or {}),
                "course_ref": course_result.course_ref_snapshot,
                "course_id": course_result.course_id,
                "canvas_course_id": raw_result.get("course_id"),
                "course_name": course_result.course_name_snapshot,
                "row_status": course_result.status,
                "announcement_id": course_result.announcement_id,
                "announcement_url": course_result.announcement_url,
                "published": course_result.published,
                "delayed_post_at": course_result.delayed_post_at,
                "dry_run": course_result.dry_run,
                "raw_result": raw_result,
            }

    def record_announcement_edit(
        self,
        *,
        job_public_id: str,
        course_ref: str,
        announcement_id: int | str,
        title: str,
        message_html: str,
        lock_comment: bool,
        canvas_response: dict,
    ) -> dict | None:
        normalized_job_id = str(job_public_id or "").strip()
        normalized_course_ref = str(course_ref or "").strip()
        normalized_announcement_id = str(announcement_id or "").strip()
        now = utc_now()
        edited_at = datetime_to_iso(now)

        with self.database.session_scope() as session:
            row = session.scalar(
                select(JobRun)
                .options(selectinload(JobRun.course_results))
                .where(JobRun.public_id == normalized_job_id)
            )
            if row is None:
                return None

            course_result = next(
                (
                    item
                    for item in row.course_results
                    if item.course_ref_snapshot == normalized_course_ref
                    and str(item.announcement_id or "") == normalized_announcement_id
                ),
                None,
            )
            if course_result is None:
                return None

            raw_result = dict(course_result.raw_result_json or {})
            edit_history = list(raw_result.get("edit_history") or [])
            edit_history.append(
                {
                    "edited_at": edited_at,
                    "title": title,
                    "lock_comment": lock_comment,
                }
            )

            raw_result.update(
                {
                    "title": title,
                    "message_html": message_html,
                    "lock_comment": lock_comment,
                    "edited": True,
                    "edited_at": edited_at,
                    "edit_history": edit_history,
                    "last_canvas_response": {
                        "id": canvas_response.get("id"),
                        "html_url": canvas_response.get("html_url"),
                        "published": canvas_response.get("published"),
                    },
                }
            )

            course_result.raw_result_json = raw_result
            course_result.announcement_url = canvas_response.get("html_url") or course_result.announcement_url
            if "published" in canvas_response:
                course_result.published = canvas_response.get("published")
            course_result.error_message = None
            course_result.updated_at = now
            row.updated_at = now
            session.flush()
            session.refresh(course_result)
            return self._serialize_course_result(course_result)

    def _sync_targets(self, session, job_row: JobRun, summary: dict) -> None:
        existing_group_map = {item.group_public_id: item for item in job_row.target_groups}
        desired_group_ids = [str(item) for item in summary.get("group_ids", []) if str(item).strip()]
        now = utc_now()
        if desired_group_ids:
            groups = session.scalars(select(CourseGroup).where(CourseGroup.public_id.in_(desired_group_ids))).all()
            group_lookup = {item.public_id: item for item in groups}
            for group_public_id in desired_group_ids:
                if group_public_id in existing_group_map:
                    continue
                group = group_lookup.get(group_public_id)
                session.add(
                    JobTargetGroup(
                        job_run_id=job_row.id,
                        group_id=group.id if group else None,
                        group_public_id=group_public_id,
                        group_name_snapshot=group.name if group else "",
                        created_at=now,
                    )
                )

        existing_course_map = {item.course_ref_snapshot: item for item in job_row.target_courses}
        desired_course_refs = [str(item) for item in summary.get("course_refs", []) if str(item).strip()]
        if desired_course_refs:
            courses = session.scalars(select(Course).where(Course.course_ref.in_(desired_course_refs))).all()
            course_lookup = {item.course_ref: item for item in courses}
            for course_ref in desired_course_refs:
                if course_ref in existing_course_map:
                    continue
                course = course_lookup.get(course_ref)
                session.add(
                    JobTargetCourse(
                        job_run_id=job_row.id,
                        course_id=course.id if course else None,
                        course_ref_snapshot=course_ref,
                        course_name_snapshot=course.course_name if course else "",
                        created_at=now,
                    )
                )

    def _replace_course_results(self, session, job_row: JobRun, rows: list[dict]) -> None:
        for item in list(job_row.course_results):
            session.delete(item)

        if not rows:
            return

        course_refs = [str(item.get("course_ref") or "").strip() for item in rows if str(item.get("course_ref") or "").strip()]
        course_lookup = {
            item.course_ref: item
            for item in session.scalars(select(Course).where(Course.course_ref.in_(course_refs))).all()
        }
        now = utc_now()
        for row in rows:
            course_ref = str(row.get("course_ref") or "").strip()
            course = course_lookup.get(course_ref)
            session.add(
                JobCourseResult(
                    job_run_id=job_row.id,
                    course_id=course.id if course else None,
                    course_ref_snapshot=course_ref,
                    course_name_snapshot=(course.course_name if course else row.get("course_name") or ""),
                    status=row.get("status") or "unknown",
                    strategy_requested=row.get("strategy_requested") or "",
                    strategy_used=row.get("strategy_used") or "",
                    students_found=int(row.get("students_found") or 0),
                    manual_matches=int(row.get("manual_matches") or 0),
                    duplicates_skipped=int(row.get("duplicates_skipped") or 0),
                    recipients_targeted=int(row.get("recipients_targeted") or 0),
                    recipients_sent=int(row.get("recipients_sent") or 0),
                    batch_count=int(row.get("batch_count") or 0),
                    announcement_id=row.get("announcement_id"),
                    announcement_url=row.get("announcement_url"),
                    conversation_ids_json=row.get("conversation_ids") or [],
                    published=row.get("published"),
                    delayed_post_at=row.get("delayed_post_at"),
                    dry_run=bool(row.get("dry_run")),
                    messageable_context=bool(row.get("messageable_context")),
                    manual_recipients=bool(row.get("manual_recipients")),
                    error_message=row.get("error"),
                    raw_result_json=row,
                    created_at=now,
                    updated_at=now,
                )
            )

    def _serialize_job(self, row: JobRun, *, include_logs: bool) -> dict:
        if row is None:
            return None
        result = dict(row.result_json or {}) if row.result_json is not None else None
        course_results = [self._serialize_course_result(item) for item in sorted(row.course_results, key=lambda item: item.id)]
        if result is not None:
            result["course_results"] = course_results
        return {
            "id": row.public_id,
            "kind": row.kind,
            "title": row.title,
            "status": row.status,
            "created_at": datetime_to_iso(row.created_at),
            "updated_at": datetime_to_iso(row.updated_at),
            "started_at": datetime_to_iso(row.started_at),
            "finished_at": datetime_to_iso(row.finished_at),
            "progress": {
                "current": row.progress_current,
                "total": row.progress_total,
                "percent": row.progress_percent,
                "step": row.progress_step,
            },
            "summary": row.summary_json or {},
            "result": result,
            "error": row.error_message,
            "logs": [self._serialize_log(item) for item in sorted(row.logs, key=lambda item: item.id)] if include_logs else [],
            "report_filename": row.report_filename,
        }

    @staticmethod
    def _serialize_log(row: JobLog) -> dict:
        return {
            "timestamp": datetime_to_iso(row.created_at),
            "level": row.level,
            "message": row.message,
            "data": row.data_json or {},
        }

    @staticmethod
    def _serialize_course_result(row: JobCourseResult) -> dict:
        raw_result = row.raw_result_json or {}
        return {
            "course_ref": row.course_ref_snapshot,
            "course_id": row.course_id,
            "course_name": row.course_name_snapshot,
            "status": row.status,
            "strategy_requested": row.strategy_requested,
            "strategy_used": row.strategy_used,
            "students_found": row.students_found,
            "manual_matches": row.manual_matches,
            "duplicates_skipped": row.duplicates_skipped,
            "recipients_targeted": row.recipients_targeted,
            "recipients_sent": row.recipients_sent,
            "batch_count": row.batch_count,
            "announcement_id": row.announcement_id,
            "announcement_url": row.announcement_url,
            "announcement_title": raw_result.get("title") or "",
            "announcement_message_html": raw_result.get("message_html") or "",
            "announcement_lock_comment": raw_result.get("lock_comment"),
            "announcement_edited": bool(raw_result.get("edited")),
            "announcement_edited_at": raw_result.get("edited_at"),
            "attachment_name": raw_result.get("attachment_name") or "",
            "conversation_ids": row.conversation_ids_json or [],
            "published": row.published,
            "delayed_post_at": row.delayed_post_at,
            "dry_run": row.dry_run,
            "messageable_context": row.messageable_context,
            "manual_recipients": row.manual_recipients,
            "error": row.error_message,
        }

    @staticmethod
    def _from_iso(value: str | None):
        if not value:
            return None
        from datetime import datetime

        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


class ReportRepository:
    def __init__(self, database):
        self.database = database

    def analytics(self, *, days: int = 30) -> dict:
        window_days = max(int(days or 30), 1)
        current_end = utc_now()
        current_start = current_end - timedelta(days=window_days)
        previous_start = current_start - timedelta(days=window_days)
        with self.database.session_scope() as session:
            jobs = session.scalars(
                select(JobRun)
                .options(selectinload(JobRun.target_groups), selectinload(JobRun.course_results))
                .where(JobRun.created_at >= previous_start)
                .order_by(JobRun.created_at.desc())
            ).all()
            recurrences = session.scalars(
                select(AnnouncementRecurrence)
                .options(selectinload(AnnouncementRecurrence.items))
                .order_by(AnnouncementRecurrence.created_at.desc())
            ).all()

        now = utc_now()
        current_jobs: list[JobRun] = []
        previous_jobs: list[JobRun] = []
        for job in jobs:
            created_at = _as_utc(job.created_at) or current_end
            if created_at >= current_start:
                current_jobs.append(job)
            elif created_at >= previous_start:
                previous_jobs.append(job)

        current_stats = self._collect_job_stats(current_jobs)
        previous_stats = self._collect_job_stats(previous_jobs)

        top_recurrences = defaultdict(lambda: {"name": "", "total_items": 0, "future_items": 0, "canceled_items": 0})
        for recurrence in recurrences:
            item_bucket = top_recurrences[recurrence.public_id]
            item_bucket["name"] = recurrence.name
            item_bucket["total_items"] = len(recurrence.items)
            item_bucket["future_items"] = len(
                [
                    item
                    for item in recurrence.items
                    if (_as_utc(item.scheduled_for) or now) >= now and item.status in {"scheduled", "created"}
                ]
            )
            item_bucket["canceled_items"] = len(
                [item for item in recurrence.items if item.status == "canceled"]
            )

        active_recurrences = len([item for item in recurrences if item.is_active and not item.is_deleted])
        recurrence_creations_current = len(
            [item for item in recurrences if (_as_utc(item.created_at) or now) >= current_start]
        )
        recurrence_creations_previous = len(
            [
                item
                for item in recurrences
                if previous_start <= (_as_utc(item.created_at) or now) < current_start
            ]
        )
        overview = {
            "days": window_days,
            "current_start": datetime_to_iso(current_start),
            "current_end": datetime_to_iso(current_end),
            "previous_start": datetime_to_iso(previous_start),
            "previous_end": datetime_to_iso(current_start),
            "total_jobs": current_stats["total_jobs"],
            "completed_jobs": current_stats["completed_jobs"],
            "failed_jobs": current_stats["failed_jobs"],
            "success_rate": current_stats["success_rate"],
            "avg_duration_seconds": current_stats["avg_duration_seconds"],
            "total_recipients_sent": current_stats["total_recipients_sent"],
            "total_announcements_created": current_stats["total_announcements_created"],
            "total_engagement_jobs": current_stats["total_engagement_jobs"],
            "active_recurrences": active_recurrences,
            "new_recurrences_created": recurrence_creations_current,
            "comparison": {
                "total_jobs": self._comparison_bucket(current_stats["total_jobs"], previous_stats["total_jobs"]),
                "completed_jobs": self._comparison_bucket(current_stats["completed_jobs"], previous_stats["completed_jobs"]),
                "failed_jobs": self._comparison_bucket(current_stats["failed_jobs"], previous_stats["failed_jobs"]),
                "success_rate": self._comparison_bucket(current_stats["success_rate"], previous_stats["success_rate"]),
                "avg_duration_seconds": self._comparison_bucket(current_stats["avg_duration_seconds"], previous_stats["avg_duration_seconds"]),
                "total_recipients_sent": self._comparison_bucket(current_stats["total_recipients_sent"], previous_stats["total_recipients_sent"]),
                "total_announcements_created": self._comparison_bucket(current_stats["total_announcements_created"], previous_stats["total_announcements_created"]),
                "total_engagement_jobs": self._comparison_bucket(current_stats["total_engagement_jobs"], previous_stats["total_engagement_jobs"]),
                "new_recurrences_created": self._comparison_bucket(recurrence_creations_current, recurrence_creations_previous),
            },
        }

        recurrence_items = [{"recurrence_id": key, **value} for key, value in sorted(top_recurrences.items(), key=lambda item: item[1]["total_items"], reverse=True)[:10]]
        upcoming_recurrence_items = [
            {
                "recurrence_id": item.public_id,
                "name": item.name,
                "title": item.title,
                "first_publish_at": datetime_to_iso(item.first_publish_at),
                "occurrence_count": item.occurrence_count,
                "future_items": len(
                    [
                        recurrence_item
                        for recurrence_item in item.items
                        if (_as_utc(recurrence_item.scheduled_for) or now) >= now and recurrence_item.status in {"scheduled", "created"}
                    ]
                ),
            }
            for item in recurrences
            if item.is_active and not item.is_deleted
        ][:10]

        return {
            "overview": overview,
            "executive": self._build_executive_summary(
                overview=overview,
                current_stats=current_stats,
                previous_stats=previous_stats,
                upcoming_recurrence_items=upcoming_recurrence_items,
            ),
            "sections": {
                "period_comparison": {"title": "Comparativo do periodo", "items": self._period_comparison_items(overview)},
                "operational": {"title": "Operacional por tipo", "items": self._kind_comparison_items(current_stats["by_kind"], previous_stats["by_kind"])},
                "daily_volume": {"title": "Volume diario do periodo atual", "items": current_stats["daily_items"]},
                "top_courses": {"title": "Cursos mais movimentados", "items": self._course_comparison_items(current_stats["top_courses"], previous_stats["top_courses"])},
                "top_groups": {"title": "Grupos mais usados", "items": self._group_comparison_items(current_stats["top_groups"], previous_stats["top_groups"])},
                "active_recurrences": {"title": "Recorrencias mais carregadas", "items": recurrence_items},
                "upcoming_recurrences": {"title": "Recorrencias ativas", "items": upcoming_recurrence_items},
                "recent_failures": {"title": "Falhas recentes", "items": current_stats["recent_failures"][:15]},
            },
        }

    def _build_executive_summary(
        self,
        *,
        overview: dict,
        current_stats: dict,
        previous_stats: dict,
        upcoming_recurrence_items: list[dict],
    ) -> dict:
        comparison = overview.get("comparison", {})
        alerts: list[dict] = []

        failed_jobs_cmp = comparison.get("failed_jobs", {})
        success_rate_cmp = comparison.get("success_rate", {})
        recipients_cmp = comparison.get("total_recipients_sent", {})

        if overview.get("failed_jobs", 0) > 0:
            level = "error" if failed_jobs_cmp.get("delta", 0) > 0 else "warning"
            alerts.append(
                {
                    "level": level,
                    "title": "Falhas operacionais no periodo",
                    "message": (
                        f"{overview.get('failed_jobs', 0)} lote(s) falharam na janela atual "
                        f"contra {int(failed_jobs_cmp.get('previous', 0))} no periodo anterior."
                    ),
                    "action": "Revise a secao 'Falhas recentes' e os cursos com maior concentracao de erro.",
                }
            )
        elif failed_jobs_cmp.get("previous", 0) > 0 and overview.get("failed_jobs", 0) == 0:
            alerts.append(
                {
                    "level": "success",
                    "title": "Recuperacao de estabilidade",
                    "message": "Nao houve falhas no periodo atual, mesmo com falhas registradas na janela anterior.",
                    "action": "Mantenha os mesmos grupos, cursos e estrategias que estabilizaram a operacao.",
                }
            )

        if overview.get("success_rate", 0) < 85 or success_rate_cmp.get("delta", 0) < -5:
            alerts.append(
                {
                    "level": "warning",
                    "title": "Taxa de sucesso abaixo do ideal",
                    "message": (
                        f"Taxa atual de {overview.get('success_rate', 0)}% "
                        f"contra {success_rate_cmp.get('previous', 0)}% no periodo anterior."
                    ),
                    "action": "Use o pre-envio e revise credenciais, turmas e anexos antes dos proximos disparos.",
                }
            )

        if overview.get("total_jobs", 0) == 0:
            alerts.append(
                {
                    "level": "info",
                    "title": "Sem atividade operacional",
                    "message": "Nenhum lote foi registrado na janela atual.",
                    "action": "Ajuste o periodo ou execute um lote para iniciar a leitura comparativa.",
                }
            )
        elif recipients_cmp.get("delta", 0) > 0 and overview.get("success_rate", 0) >= 90:
            alerts.append(
                {
                    "level": "success",
                    "title": "Volume cresceu com boa estabilidade",
                    "message": (
                        f"Foram {overview.get('total_recipients_sent', 0)} destinatarios no periodo atual, "
                        f"com delta de {int(recipients_cmp.get('delta', 0))} frente ao anterior."
                    ),
                    "action": "Bom momento para ampliar grupos e rotinas recorrentes sem perder controle operacional.",
                }
            )

        top_failure_course = next(
            (
                item
                for item in self._course_comparison_items(current_stats["top_courses"], previous_stats["top_courses"])
                if item.get("current_failure", 0) > 0
            ),
            None,
        )
        if top_failure_course:
            alerts.append(
                {
                    "level": "warning",
                    "title": "Curso com falhas concentradas",
                    "message": (
                        f"{top_failure_course.get('course_name') or top_failure_course.get('course_ref')} "
                        f"registrou {top_failure_course.get('current_failure', 0)} falha(s) no periodo atual."
                    ),
                    "action": "Priorize este curso no proximo teste de envio ou no diagnostico de permissao/acesso.",
                }
            )

        next_recurrence = self._next_upcoming_recurrence(upcoming_recurrence_items)
        if next_recurrence:
            alerts.append(
                {
                    "level": "info",
                    "title": "Recorrencia proxima de disparar",
                    "message": (
                        f"{next_recurrence.get('name') or 'Recorrencia'} tem publicacao prevista em "
                        f"{datetime_to_iso(next_recurrence.get('first_publish_at')) if isinstance(next_recurrence.get('first_publish_at'), datetime) else next_recurrence.get('first_publish_at') or '-'}."
                    ),
                    "action": "Revise o curso e a mensagem caso o calendario da disciplina tenha mudado.",
                }
            )

        top_course = self._top_course_highlight(current_stats["top_courses"])
        top_group = self._top_group_highlight(current_stats["top_groups"])
        highlights = []
        if top_course:
            highlights.append(top_course)
        if top_group:
            highlights.append(top_group)
        if top_failure_course:
            highlights.append(
                {
                    "label": "Maior foco de erro",
                    "value": top_failure_course.get("course_name") or top_failure_course.get("course_ref") or "-",
                    "helper": (
                        f"{top_failure_course.get('current_failure', 0)} falha(s) agora | "
                        f"{top_failure_course.get('previous_failure', 0)} antes"
                    ),
                    "tone": "warning",
                }
            )
        if next_recurrence:
            highlights.append(
                {
                    "label": "Proxima recorrencia",
                    "value": next_recurrence.get("name") or "-",
                    "helper": format_datetime_short(next_recurrence.get("first_publish_at")),
                    "tone": "info",
                }
            )
        if not highlights:
            highlights.append(
                {
                    "label": "Painel estavel",
                    "value": "Sem destaques criticos",
                    "helper": "Use os filtros do periodo para aprofundar a leitura.",
                    "tone": "success",
                }
            )

        return {
            "alerts": alerts[:5],
            "highlights": highlights[:4],
        }

    def _collect_job_stats(self, jobs: list[JobRun]) -> dict:
        durations = []
        daily = defaultdict(lambda: {"announcement": 0, "message": 0, "engagement": 0, "completed": 0, "failed": 0})
        by_kind = defaultdict(lambda: {"jobs": 0, "completed": 0, "failed": 0, "dry_run": 0, "recipients_sent": 0, "announcements": 0})
        top_courses = defaultdict(lambda: {"course_name": "", "runs": 0, "success": 0, "failure": 0, "recipients_sent": 0, "announcements": 0})
        top_groups = defaultdict(lambda: {"group_name": "", "jobs": 0})
        recent_failures = []
        total_recipients_sent = 0
        total_announcements = 0

        for job in jobs:
            if job.started_at and job.finished_at:
                durations.append((_as_utc(job.finished_at) - _as_utc(job.started_at)).total_seconds())

            created_at = _as_utc(job.created_at) or utc_now()
            day_key = created_at.date().isoformat()
            daily[day_key][job.kind] += 1
            if job.status == "completed":
                daily[day_key]["completed"] += 1
            if job.status == "failed":
                daily[day_key]["failed"] += 1

            kind_bucket = by_kind[job.kind]
            kind_bucket["jobs"] += 1
            if job.status == "completed":
                kind_bucket["completed"] += 1
            if job.status == "failed":
                kind_bucket["failed"] += 1
            if job.dry_run:
                kind_bucket["dry_run"] += 1

            for target_group in job.target_groups:
                group_key = target_group.group_public_id or target_group.group_name_snapshot
                group_bucket = top_groups[group_key]
                group_bucket["group_name"] = target_group.group_name_snapshot or target_group.group_public_id
                group_bucket["jobs"] += 1

            for result in job.course_results:
                course_key = result.course_ref_snapshot or str(result.course_id or "")
                course_bucket = top_courses[course_key]
                course_bucket["course_name"] = result.course_name_snapshot or course_key
                course_bucket["runs"] += 1
                if result.status == "success":
                    course_bucket["success"] += 1
                if result.status == "error":
                    course_bucket["failure"] += 1
                course_bucket["recipients_sent"] += result.recipients_sent
                kind_bucket["recipients_sent"] += result.recipients_sent
                total_recipients_sent += result.recipients_sent
                if result.announcement_id:
                    course_bucket["announcements"] += 1
                    kind_bucket["announcements"] += 1
                    total_announcements += 1
                if result.error_message:
                    recent_failures.append(
                        {
                            "job_id": job.public_id,
                            "kind": job.kind,
                            "course_ref": result.course_ref_snapshot,
                            "course_name": result.course_name_snapshot,
                            "status": result.status,
                            "error": result.error_message,
                            "created_at": datetime_to_iso(created_at),
                        }
                    )

        total_jobs = len(jobs)
        completed_jobs = len([item for item in jobs if item.status == "completed"])
        failed_jobs = len([item for item in jobs if item.status == "failed"])
        for item in by_kind.values():
            item["success_rate"] = round((item["completed"] / item["jobs"]) * 100, 2) if item["jobs"] else 0

        return {
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "success_rate": round((completed_jobs / total_jobs) * 100, 2) if total_jobs else 0,
            "avg_duration_seconds": round(sum(durations) / len(durations), 2) if durations else 0,
            "total_recipients_sent": total_recipients_sent,
            "total_announcements_created": total_announcements,
            "total_engagement_jobs": by_kind.get("engagement", {}).get("jobs", 0),
            "daily_items": [{"date": key, **value} for key, value in sorted(daily.items(), key=lambda item: item[0], reverse=True)],
            "by_kind": dict(by_kind),
            "top_courses": dict(top_courses),
            "top_groups": dict(top_groups),
            "recent_failures": recent_failures,
        }

    @staticmethod
    def _comparison_bucket(current_value, previous_value) -> dict:
        current_numeric = round(float(current_value or 0), 2)
        previous_numeric = round(float(previous_value or 0), 2)
        delta = round(current_numeric - previous_numeric, 2)
        if previous_numeric == 0:
            delta_percent = 0 if current_numeric == 0 else None
        else:
            delta_percent = round((delta / previous_numeric) * 100, 2)
        direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
        return {
            "current": current_numeric,
            "previous": previous_numeric,
            "delta": delta,
            "delta_percent": delta_percent,
            "direction": direction,
            "baseline_empty": previous_numeric == 0,
        }

    def _period_comparison_items(self, overview: dict) -> list[dict]:
        labels = {
            "total_jobs": "Lotes",
            "completed_jobs": "Concluidos",
            "failed_jobs": "Falhas",
            "success_rate": "Taxa de sucesso",
            "avg_duration_seconds": "Duracao media (s)",
            "total_recipients_sent": "Mensagens enviadas",
            "total_announcements_created": "Comunicados criados",
            "total_engagement_jobs": "Envios para inativos",
            "new_recurrences_created": "Novas recorrencias",
        }
        return [
            {"metric": labels[key], **value}
            for key, value in overview.get("comparison", {}).items()
            if key in labels
        ]

    def _kind_comparison_items(self, current_map: dict, previous_map: dict) -> list[dict]:
        items = []
        for key in sorted(set(current_map) | set(previous_map)):
            current_item = current_map.get(key, {})
            previous_item = previous_map.get(key, {})
            items.append(
                {
                    "kind": key,
                    "current_jobs": current_item.get("jobs", 0),
                    "previous_jobs": previous_item.get("jobs", 0),
                    "delta_jobs": current_item.get("jobs", 0) - previous_item.get("jobs", 0),
                    "current_completed": current_item.get("completed", 0),
                    "previous_completed": previous_item.get("completed", 0),
                    "current_failed": current_item.get("failed", 0),
                    "previous_failed": previous_item.get("failed", 0),
                    "current_dry_run": current_item.get("dry_run", 0),
                    "previous_dry_run": previous_item.get("dry_run", 0),
                    "current_success_rate": current_item.get("success_rate", 0),
                    "previous_success_rate": previous_item.get("success_rate", 0),
                    "current_recipients_sent": current_item.get("recipients_sent", 0),
                    "previous_recipients_sent": previous_item.get("recipients_sent", 0),
                    "current_announcements": current_item.get("announcements", 0),
                    "previous_announcements": previous_item.get("announcements", 0),
                }
            )
        return items

    def _course_comparison_items(self, current_map: dict, previous_map: dict) -> list[dict]:
        items = []
        for key in set(current_map) | set(previous_map):
            current_item = current_map.get(key, {})
            previous_item = previous_map.get(key, {})
            items.append(
                {
                    "course_ref": key,
                    "course_name": current_item.get("course_name") or previous_item.get("course_name") or key,
                    "current_runs": current_item.get("runs", 0),
                    "previous_runs": previous_item.get("runs", 0),
                    "delta_runs": current_item.get("runs", 0) - previous_item.get("runs", 0),
                    "current_success": current_item.get("success", 0),
                    "previous_success": previous_item.get("success", 0),
                    "current_failure": current_item.get("failure", 0),
                    "previous_failure": previous_item.get("failure", 0),
                    "current_recipients_sent": current_item.get("recipients_sent", 0),
                    "previous_recipients_sent": previous_item.get("recipients_sent", 0),
                    "delta_recipients_sent": current_item.get("recipients_sent", 0) - previous_item.get("recipients_sent", 0),
                    "current_announcements": current_item.get("announcements", 0),
                    "previous_announcements": previous_item.get("announcements", 0),
                }
            )
        return sorted(
            items,
            key=lambda item: (item["current_runs"], item["previous_runs"], item["current_recipients_sent"]),
            reverse=True,
        )[:10]

    def _group_comparison_items(self, current_map: dict, previous_map: dict) -> list[dict]:
        items = []
        for key in set(current_map) | set(previous_map):
            current_item = current_map.get(key, {})
            previous_item = previous_map.get(key, {})
            items.append(
                {
                    "group_id": key,
                    "group_name": current_item.get("group_name") or previous_item.get("group_name") or key,
                    "current_jobs": current_item.get("jobs", 0),
                    "previous_jobs": previous_item.get("jobs", 0),
                    "delta_jobs": current_item.get("jobs", 0) - previous_item.get("jobs", 0),
                }
            )
        return sorted(items, key=lambda item: (item["current_jobs"], item["previous_jobs"]), reverse=True)[:10]

    @staticmethod
    def _top_course_highlight(current_map: dict) -> dict | None:
        if not current_map:
            return None
        key, item = max(
            current_map.items(),
            key=lambda pair: (pair[1].get("runs", 0), pair[1].get("recipients_sent", 0)),
        )
        return {
            "label": "Curso mais acionado",
            "value": item.get("course_name") or key,
            "helper": f"{item.get('runs', 0)} execucao(oes) | {item.get('recipients_sent', 0)} mensagens",
            "tone": "info",
        }

    @staticmethod
    def _top_group_highlight(current_map: dict) -> dict | None:
        if not current_map:
            return None
        key, item = max(current_map.items(), key=lambda pair: pair[1].get("jobs", 0))
        return {
            "label": "Grupo mais usado",
            "value": item.get("group_name") or key,
            "helper": f"{item.get('jobs', 0)} lote(s) no periodo",
            "tone": "info",
        }

    @staticmethod
    def _next_upcoming_recurrence(upcoming_items: list[dict]) -> dict | None:
        sorted_items = sorted(
            [item for item in upcoming_items if item.get("first_publish_at")],
            key=lambda item: item.get("first_publish_at") or "",
        )
        return sorted_items[0] if sorted_items else None


def format_datetime_short(value) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        resolved = _as_utc(value)
        return resolved.strftime("%d/%m %H:%M") if resolved else "-"
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return str(value)
    resolved = _as_utc(parsed)
    return resolved.strftime("%d/%m %H:%M") if resolved else "-"


class AnnouncementRecurrenceRepository:
    def __init__(self, database):
        self.database = database

    def list_recurrences(self, *, active_only: bool | None = True) -> list[dict]:
        with self.database.session_scope() as session:
            stmt = (
                select(AnnouncementRecurrence)
                .options(selectinload(AnnouncementRecurrence.items))
                .order_by(AnnouncementRecurrence.created_at.desc())
            )
            if active_only is True:
                stmt = stmt.where(AnnouncementRecurrence.is_active.is_(True), AnnouncementRecurrence.is_deleted.is_(False))
            elif active_only is False:
                stmt = stmt.where(AnnouncementRecurrence.is_active.is_(False))
            rows = session.scalars(stmt).all()
            return [self._serialize_recurrence(item) for item in rows]

    def get_recurrence(self, public_id: str, *, active_only: bool | None = None) -> dict | None:
        normalized = str(public_id or "").strip()
        if not normalized:
            return None
        with self.database.session_scope() as session:
            stmt = (
                select(AnnouncementRecurrence)
                .options(selectinload(AnnouncementRecurrence.items))
                .where(AnnouncementRecurrence.public_id == normalized)
            )
            if active_only is True:
                stmt = stmt.where(AnnouncementRecurrence.is_active.is_(True), AnnouncementRecurrence.is_deleted.is_(False))
            row = session.scalar(stmt)
            return self._serialize_recurrence(row) if row else None

    def create_recurrence(self, payload: dict, items: list[dict]) -> dict:
        now = utc_now()
        with self.database.session_scope() as session:
            row = AnnouncementRecurrence(
                public_id=uuid4().hex[:12],
                name=payload["name"],
                title=payload["title"],
                message_html=payload["message_html"],
                lock_comment=bool(payload.get("lock_comment")),
                target_mode=payload.get("target_mode") or "groups",
                target_config_json=payload.get("target_config_json") or {},
                recurrence_type=payload["recurrence_type"],
                interval_value=int(payload["interval_value"]),
                occurrence_count=int(payload["occurrence_count"]),
                first_publish_at=payload["first_publish_at"],
                client_timezone=payload.get("client_timezone") or "UTC",
                base_url_snapshot=payload.get("base_url_snapshot") or "",
                canvas_user_id=payload.get("canvas_user_id"),
                canvas_user_name=payload.get("canvas_user_name") or "",
                last_error=payload.get("last_error"),
                created_at=now,
                updated_at=now,
                activated_at=now,
            )
            session.add(row)
            session.flush()

            for item in items:
                session.add(
                    AnnouncementRecurrenceItem(
                        recurrence_id=row.id,
                        occurrence_index=int(item["occurrence_index"]),
                        course_ref_snapshot=item.get("course_ref_snapshot") or "",
                        course_id_snapshot=item.get("course_id_snapshot"),
                        course_name_snapshot=item.get("course_name_snapshot") or "",
                        scheduled_for=item["scheduled_for"],
                        canvas_topic_id=item.get("canvas_topic_id"),
                        canvas_topic_url=item.get("canvas_topic_url"),
                        status=item.get("status") or "scheduled",
                        error_message=item.get("error_message"),
                        deleted_on_canvas=bool(item.get("deleted_on_canvas")),
                        canceled_at=item.get("canceled_at"),
                        created_at=now,
                        updated_at=now,
                    )
                )

            session.flush()
            session.refresh(row)
            return self._serialize_recurrence(row)

    def cancel_recurrence(self, public_id: str, *, cancel_reason: str, item_updates: list[dict]) -> dict:
        normalized = str(public_id or "").strip()
        with self.database.session_scope() as session:
            row = session.scalar(
                select(AnnouncementRecurrence)
                .options(selectinload(AnnouncementRecurrence.items))
                .where(AnnouncementRecurrence.public_id == normalized)
            )
            if row is None:
                raise ValueError("Recorrencia de avisos nao encontrada.")

            now = utc_now()
            row.is_active = False
            row.is_deleted = False
            row.deactivated_at = now
            row.canceled_at = now
            row.cancel_reason = cancel_reason or ""
            row.updated_at = now

            updates_by_id = {int(item["item_id"]): item for item in item_updates if item.get("item_id") is not None}
            for item in row.items:
                update_data = updates_by_id.get(item.id)
                if not update_data:
                    continue
                item.status = update_data.get("status") or item.status
                item.error_message = update_data.get("error_message")
                item.deleted_on_canvas = bool(update_data.get("deleted_on_canvas"))
                item.canceled_at = update_data.get("canceled_at") or now
                item.updated_at = now

            session.flush()
            session.refresh(row)
            return self._serialize_recurrence(row)

    def update_recurrence(self, public_id: str, *, payload: dict, replace_item_ids: list[int], new_items: list[dict]) -> dict:
        normalized = str(public_id or "").strip()
        with self.database.session_scope() as session:
            row = session.scalar(
                select(AnnouncementRecurrence)
                .options(selectinload(AnnouncementRecurrence.items))
                .where(AnnouncementRecurrence.public_id == normalized)
            )
            if row is None:
                raise ValueError("Recorrencia de avisos nao encontrada.")

            now = utc_now()
            replace_ids = {int(item_id) for item_id in replace_item_ids}
            for item in list(row.items):
                if item.id in replace_ids:
                    session.delete(item)
            session.flush()

            row.name = payload["name"]
            row.title = payload["title"]
            row.message_html = payload["message_html"]
            row.lock_comment = bool(payload.get("lock_comment"))
            row.target_mode = payload.get("target_mode") or "groups"
            row.target_config_json = payload.get("target_config_json") or {}
            row.recurrence_type = payload["recurrence_type"]
            row.interval_value = int(payload["interval_value"])
            row.occurrence_count = int(payload["occurrence_count"])
            row.first_publish_at = payload["first_publish_at"]
            row.client_timezone = payload.get("client_timezone") or "UTC"
            row.base_url_snapshot = payload.get("base_url_snapshot") or ""
            row.canvas_user_id = payload.get("canvas_user_id")
            row.canvas_user_name = payload.get("canvas_user_name") or ""
            row.last_error = payload.get("last_error")
            row.is_active = True
            row.is_deleted = False
            row.deactivated_at = None
            row.deleted_at = None
            row.canceled_at = None
            row.cancel_reason = None
            row.activated_at = row.activated_at or now
            row.updated_at = now

            for item in new_items:
                session.add(
                    AnnouncementRecurrenceItem(
                        recurrence_id=row.id,
                        occurrence_index=int(item["occurrence_index"]),
                        course_ref_snapshot=item.get("course_ref_snapshot") or "",
                        course_id_snapshot=item.get("course_id_snapshot"),
                        course_name_snapshot=item.get("course_name_snapshot") or "",
                        scheduled_for=item["scheduled_for"],
                        canvas_topic_id=item.get("canvas_topic_id"),
                        canvas_topic_url=item.get("canvas_topic_url"),
                        status=item.get("status") or "scheduled",
                        error_message=item.get("error_message"),
                        deleted_on_canvas=bool(item.get("deleted_on_canvas")),
                        canceled_at=item.get("canceled_at"),
                        created_at=now,
                        updated_at=now,
                    )
                )

            session.flush()
            session.expire(row, ["items"])
            session.refresh(row)
            return self._serialize_recurrence(row)

    @staticmethod
    def _serialize_item(row: AnnouncementRecurrenceItem, timezone_name: str | None = None) -> dict:
        return {
            "item_id": row.id,
            "occurrence_index": row.occurrence_index,
            "course_ref": row.course_ref_snapshot,
            "course_id": row.course_id_snapshot,
            "course_name": row.course_name_snapshot,
            "scheduled_for": datetime_to_iso(_with_timezone(row.scheduled_for, timezone_name)),
            "canvas_topic_id": row.canvas_topic_id,
            "canvas_topic_url": row.canvas_topic_url,
            "status": row.status,
            "error_message": row.error_message,
            "deleted_on_canvas": row.deleted_on_canvas,
            "canceled_at": datetime_to_iso(row.canceled_at),
            "created_at": datetime_to_iso(row.created_at),
            "updated_at": datetime_to_iso(row.updated_at),
        }

    @classmethod
    def _serialize_recurrence(cls, row: AnnouncementRecurrence | None) -> dict | None:
        if row is None:
            return None
        now = utc_now()
        timezone_name = row.client_timezone or "UTC"
        items = [cls._serialize_item(item, timezone_name) for item in sorted(row.items, key=lambda entry: (entry.scheduled_for, entry.course_ref_snapshot, entry.occurrence_index))]
        future_items = [
            item
            for item in row.items
            if (_as_utc(item.scheduled_for) or now) >= now and item.status in {"scheduled", "created"}
        ]
        return {
            "id": row.public_id,
            "name": row.name,
            "title": row.title,
            "message_html": row.message_html,
            "lock_comment": row.lock_comment,
            "target_mode": row.target_mode,
            "target_config_json": row.target_config_json or {},
            "recurrence_type": row.recurrence_type,
            "interval_value": row.interval_value,
            "occurrence_count": row.occurrence_count,
            "first_publish_at": datetime_to_iso(_with_timezone(row.first_publish_at, timezone_name)),
            "client_timezone": row.client_timezone,
            "base_url_snapshot": row.base_url_snapshot,
            "canvas_user_id": row.canvas_user_id,
            "canvas_user_name": row.canvas_user_name,
            "cancel_reason": row.cancel_reason,
            "canceled_at": datetime_to_iso(row.canceled_at),
            "last_error": row.last_error,
            "is_active": row.is_active,
            "is_deleted": row.is_deleted,
            "created_at": datetime_to_iso(row.created_at),
            "updated_at": datetime_to_iso(row.updated_at),
            "activated_at": datetime_to_iso(row.activated_at),
            "deactivated_at": datetime_to_iso(row.deactivated_at),
            "deleted_at": datetime_to_iso(row.deleted_at),
            "total_items": len(items),
            "future_items": len(future_items),
            "canceled_items": len([item for item in row.items if item.status == "canceled"]),
            "error_items": len([item for item in row.items if item.status == "error"]),
            "next_publish_at": datetime_to_iso(_with_timezone(min((item.scheduled_for for item in future_items), default=None), timezone_name)),
            "items": items,
        }


class DatabaseAdminRepository:
    def __init__(self, database):
        self.database = database

    def wipe_all_data(self) -> dict:
        with self.database.session_scope() as session:
            inspector = inspect(session.bind)
            legacy_tables = {
                table_name
                for table_name in ("campaign_runs", "campaign_schedules", "campaign_templates")
                if inspector.has_table(table_name)
            }
            counts = {
                "announcement_recurrence_items": session.query(AnnouncementRecurrenceItem).count(),
                "announcement_recurrences": session.query(AnnouncementRecurrence).count(),
                "job_logs": session.query(JobLog).count(),
                "job_course_results": session.query(JobCourseResult).count(),
                "job_target_courses": session.query(JobTargetCourse).count(),
                "job_target_groups": session.query(JobTargetGroup).count(),
                "job_runs": session.query(JobRun).count(),
                "group_courses": session.query(GroupCourse).count(),
                "course_groups": session.query(CourseGroup).count(),
                "courses": session.query(Course).count(),
            }
            for table_name in sorted(legacy_tables):
                counts[table_name] = session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar_one()
            session.execute(delete(AnnouncementRecurrenceItem))
            session.execute(delete(AnnouncementRecurrence))
            for table_name in sorted(legacy_tables):
                session.execute(text(f"DELETE FROM {table_name}"))
            session.execute(delete(JobLog))
            session.execute(delete(JobCourseResult))
            session.execute(delete(JobTargetCourse))
            session.execute(delete(JobTargetGroup))
            session.execute(delete(JobRun))
            session.execute(delete(GroupCourse))
            session.execute(delete(CourseGroup))
            session.execute(delete(Course))
            return counts
