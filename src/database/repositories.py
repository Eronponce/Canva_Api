from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from uuid import uuid4

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
        cutoff = utc_now() - timedelta(days=max(days - 1, 0))
        with self.database.session_scope() as session:
            jobs = session.scalars(
                select(JobRun)
                .options(selectinload(JobRun.target_groups), selectinload(JobRun.course_results))
                .where(JobRun.created_at >= cutoff)
                .order_by(JobRun.created_at.desc())
            ).all()
            recurrences = session.scalars(
                select(AnnouncementRecurrence)
                .options(selectinload(AnnouncementRecurrence.items))
                .order_by(AnnouncementRecurrence.created_at.desc())
            ).all()

        durations = []
        daily = defaultdict(lambda: {"announcement": 0, "message": 0, "engagement": 0, "completed": 0, "failed": 0})
        by_kind = defaultdict(lambda: {"jobs": 0, "completed": 0, "failed": 0, "dry_run": 0})
        top_courses = defaultdict(lambda: {"course_name": "", "runs": 0, "success": 0, "failure": 0, "recipients_sent": 0, "announcements": 0})
        top_groups = defaultdict(lambda: {"group_name": "", "jobs": 0})
        top_recurrences = defaultdict(lambda: {"name": "", "total_items": 0, "future_items": 0, "canceled_items": 0})
        recent_failures = []
        total_recipients_sent = 0
        total_announcements = 0

        for job in jobs:
            if job.started_at and job.finished_at:
                durations.append((job.finished_at - job.started_at).total_seconds())
            day_key = job.created_at.date().isoformat()
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
                group_bucket = top_groups[target_group.group_public_id or target_group.group_name_snapshot]
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
                if result.announcement_id:
                    course_bucket["announcements"] += 1
                    total_announcements += 1
                total_recipients_sent += result.recipients_sent
                if result.error_message:
                    recent_failures.append(
                        {
                            "job_id": job.public_id,
                            "kind": job.kind,
                            "course_ref": result.course_ref_snapshot,
                            "course_name": result.course_name_snapshot,
                            "status": result.status,
                            "error": result.error_message,
                            "created_at": datetime_to_iso(job.created_at),
                        }
                    )

        now = utc_now()
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

        total_jobs = len(jobs)
        completed_jobs = len([item for item in jobs if item.status == "completed"])
        failed_jobs = len([item for item in jobs if item.status == "failed"])
        active_recurrences = len([item for item in recurrences if item.is_active and not item.is_deleted])
        overview = {
            "days": days,
            "total_jobs": total_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
            "success_rate": round((completed_jobs / total_jobs) * 100, 2) if total_jobs else 0,
            "avg_duration_seconds": round(sum(durations) / len(durations), 2) if durations else 0,
            "total_recipients_sent": total_recipients_sent,
            "total_announcements_created": total_announcements,
            "total_engagement_jobs": by_kind.get("engagement", {}).get("jobs", 0),
            "active_recurrences": active_recurrences,
        }

        daily_items = [{"date": key, **value} for key, value in sorted(daily.items(), key=lambda item: item[0], reverse=True)]
        by_kind_items = [{"kind": key, **value} for key, value in sorted(by_kind.items(), key=lambda item: item[0])]
        top_course_items = [{"course_ref": key, **value} for key, value in sorted(top_courses.items(), key=lambda item: item[1]["runs"], reverse=True)[:10]]
        top_group_items = [{"group_id": key, **value} for key, value in sorted(top_groups.items(), key=lambda item: item[1]["jobs"], reverse=True)[:10]]
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
            "sections": {
                "operational": {"title": "Operacional por periodo", "items": by_kind_items},
                "daily_volume": {"title": "Volume diario", "items": daily_items},
                "top_courses": {"title": "Cursos mais movimentados", "items": top_course_items},
                "top_groups": {"title": "Grupos mais usados", "items": top_group_items},
                "active_recurrences": {"title": "Recorrencias mais carregadas", "items": recurrence_items},
                "upcoming_recurrences": {"title": "Recorrencias ativas", "items": upcoming_recurrence_items},
                "recent_failures": {"title": "Falhas recentes", "items": recent_failures[:15]},
            },
        }


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

    @staticmethod
    def _serialize_item(row: AnnouncementRecurrenceItem) -> dict:
        return {
            "item_id": row.id,
            "occurrence_index": row.occurrence_index,
            "course_ref": row.course_ref_snapshot,
            "course_id": row.course_id_snapshot,
            "course_name": row.course_name_snapshot,
            "scheduled_for": datetime_to_iso(row.scheduled_for),
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
        items = [cls._serialize_item(item) for item in sorted(row.items, key=lambda entry: (entry.scheduled_for, entry.course_ref_snapshot, entry.occurrence_index))]
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
            "first_publish_at": datetime_to_iso(row.first_publish_at),
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
            "next_publish_at": datetime_to_iso(min((item.scheduled_for for item in future_items), default=None)),
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
