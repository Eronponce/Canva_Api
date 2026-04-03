from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from pathlib import Path

from src.services.canvas_client import CanvasApiError
from src.utils.parsing import parse_course_references
from src.utils.time_utils import utc_now_iso


class EngagementService:
    CRITERIA_NEVER_ACCESSED = "never_accessed"
    CRITERIA_INCOMPLETE_RESOURCES = "incomplete_resources"
    CRITERIA_NEVER_OR_INCOMPLETE = "never_accessed_or_incomplete_resources"
    VALID_CRITERIA = {
        CRITERIA_NEVER_ACCESSED,
        CRITERIA_INCOMPLETE_RESOURCES,
        CRITERIA_NEVER_OR_INCOMPLETE,
    }

    def __init__(self, app_config, connection_service, job_manager):
        self.app_config = app_config
        self.connection_service = connection_service
        self.job_manager = job_manager

    def preview_targets(self, payload: dict) -> dict:
        evaluation = self._evaluate_targets(payload)
        return {
            "summary": evaluation["summary"],
            "courses": evaluation["courses"],
            "items": evaluation["items"],
        }

    def run_job(self, job_id: str, payload: dict) -> None:
        course_refs = parse_course_references(payload.get("course_ids_text", ""))
        subject_template = (payload.get("subject") or "").strip()
        body_template = (payload.get("message") or "").strip()
        criteria = self._normalize_criteria(payload.get("criteria_mode"))
        dry_run = bool(payload.get("dry_run"))

        if not course_refs:
            raise ValueError("Selecione pelo menos um grupo ou curso para a busca ativa.")
        if not subject_template:
            raise ValueError("Informe o assunto da mensagem de busca ativa.")
        if not body_template:
            raise ValueError("Informe o corpo da mensagem de busca ativa.")

        evaluation = self._evaluate_targets(payload)
        items = evaluation["items"]
        if not items:
            raise ValueError("Nenhum aluno corresponde ao criterio selecionado.")

        client = self.connection_service.build_client(payload)
        user = client.get_current_user()
        self.job_manager.update_metadata(
            job_id,
            base_url=payload.get("base_url") or "",
            request_payload={
                key: value
                for key, value in payload.items()
                if key not in {"access_token", "api_token"}
            },
            request_token_source="inline" if (payload.get("access_token") or payload.get("api_token")) else self.connection_service.app_config.default_token_source,
            requested_strategy=criteria,
            effective_strategy="individual_users",
            dry_run=dry_run,
            dedupe=False,
            canvas_user_id=user.get("id"),
            canvas_user_name=user.get("name") or user.get("short_name") or "",
        )

        total_steps = max(len(items) + len(evaluation["courses"]), 1)
        self.job_manager.mark_running(job_id, total=total_steps, step="Preparando alunos para busca ativa")
        self.job_manager.add_log(
            job_id,
            level="info",
            message="Busca ativa iniciada.",
            data={
                "criteria_mode": criteria,
                "courses_selected": len(evaluation["courses"]),
                "students_targeted": len(items),
            },
        )

        course_rows = []
        csv_rows = []
        step_index = 0

        for course in evaluation["courses"]:
            step_index += 1
            matched_items = [item for item in items if item["course_ref"] == course["course_ref"]]
            result_row = {
                "course_ref": course["course_ref"],
                "course_id": course["course_id"],
                "course_name": course["course_name"],
                "strategy_requested": criteria,
                "strategy_used": "individual_users",
                "students_found": course["students_found"],
                "manual_matches": course["matched_students"],
                "duplicates_skipped": 0,
                "recipients_targeted": len(matched_items),
                "recipients_sent": 0,
                "batch_count": 0,
                "status": "success",
                "conversation_ids": [],
                "error": None,
                "dry_run": dry_run,
                "messageable_context": True,
                "manual_recipients": True,
                "analytics_available": course["analytics_available"],
                "progress_available": course["progress_available"],
                "enrollment_activity_available": course.get("enrollment_activity_available"),
                "never_accessed_matches": course["never_accessed_matches"],
                "incomplete_resources_matches": course["incomplete_resources_matches"],
                "inactive_days_matches": course.get("inactive_days_matches", 0),
                "low_activity_matches": course.get("low_activity_matches", 0),
                "matched_students_preview": [item["student_name"] for item in matched_items[:10]],
            }

            if not matched_items:
                result_row["status"] = "skipped"
                course_rows.append(result_row)
                self.job_manager.set_progress(
                    job_id,
                    current=step_index,
                    total=total_steps,
                    step=f"Curso {course['course_name']} sem alunos alvo",
                )
                continue

            for item in matched_items:
                step_index += 1
                self.job_manager.set_progress(
                    job_id,
                    current=step_index - 1,
                    total=total_steps,
                    step=f"Enviando para {item['student_name']} em {course['course_name']}",
                )

                rendered_subject = self._render_template(
                    subject_template,
                    student_name=item["student_name"],
                    course_name=course["course_name"],
                    course_ref=course["course_ref"],
                    reason=item["reasons_label"],
                )
                rendered_body = self._render_template(
                    body_template,
                    student_name=item["student_name"],
                    course_name=course["course_name"],
                    course_ref=course["course_ref"],
                    reason=item["reasons_label"],
                )

                conversation_id = None
                send_error = None
                sent = False

                if dry_run:
                    sent = False
                else:
                    try:
                        response = client.create_conversation(
                            recipients=[item["user_id"]],
                            subject=rendered_subject,
                            body=rendered_body,
                            context_code=f"course_{course['course_id']}",
                            force_new=True,
                            group_conversation=False,
                        )
                        ids = self._extract_conversation_ids(response)
                        result_row["conversation_ids"].extend(ids)
                        result_row["recipients_sent"] += 1
                        result_row["batch_count"] += 1
                        conversation_id = ids[0] if ids else None
                        sent = True
                    except CanvasApiError as exc:
                        send_error = exc.message
                    except Exception as exc:  # noqa: BLE001
                        send_error = str(exc)

                if send_error:
                    result_row["status"] = "partial" if result_row["recipients_sent"] else "error"
                    result_row["error"] = f"{result_row['error']} | {send_error}" if result_row["error"] else send_error
                    self.job_manager.add_log(
                        job_id,
                        level="error",
                        message="Falha ao enviar mensagem de busca ativa.",
                        data={
                            "course_ref": course["course_ref"],
                            "user_id": item["user_id"],
                            "student_name": item["student_name"],
                            "error": send_error,
                        },
                    )
                else:
                    self.job_manager.add_log(
                        job_id,
                        level="info",
                        message="Aluno processado na busca ativa.",
                        data={
                            "course_ref": course["course_ref"],
                            "user_id": item["user_id"],
                            "student_name": item["student_name"],
                            "dry_run": dry_run,
                        },
                    )

                csv_rows.append(
                    {
                        "course_ref": course["course_ref"],
                        "course_id": course["course_id"],
                        "course_name": course["course_name"],
                        "user_id": item["user_id"],
                        "student_name": item["student_name"],
                        "page_views": item["page_views"],
                        "participations": item["participations"],
                        "last_activity_at": item.get("last_activity_at"),
                        "total_activity_time_seconds": item.get("total_activity_time_seconds"),
                        "requirement_count": item["requirement_count"],
                        "requirement_completed_count": item["requirement_completed_count"],
                        "completed_at": item["completed_at"],
                        "reasons": item["reasons_label"],
                        "sent": sent,
                        "dry_run": dry_run,
                        "conversation_id": conversation_id,
                        "error": send_error or "",
                    }
                )

                self.job_manager.set_progress(
                    job_id,
                    current=step_index,
                    total=total_steps,
                    step=f"Aluno {item['student_name']} concluido",
                )

            course_rows.append(result_row)

        summary = dict(evaluation["summary"])
        summary.update(
            {
                "requested_at": utc_now_iso(),
                "requested_by": {
                    "id": user.get("id"),
                    "name": user.get("name"),
                },
                "criteria_mode": criteria,
                "dry_run": dry_run,
                "requested_strategy": criteria,
                "effective_strategy": "individual_users",
                "success_count": len([row for row in course_rows if row["status"] == "success"]),
                "partial_count": len([row for row in course_rows if row["status"] == "partial"]),
                "failure_count": len([row for row in course_rows if row["status"] == "error"]),
                "skipped_count": len([row for row in course_rows if row["status"] == "skipped"]),
                "total_recipients_targeted": sum(row["recipients_targeted"] for row in course_rows),
                "total_recipients_sent": sum(row["recipients_sent"] for row in course_rows),
            }
        )

        report_filename = self._write_report(job_id, csv_rows)
        self.job_manager.complete(
            job_id,
            result={
                "summary": summary,
                "course_results": course_rows,
            },
            report_filename=report_filename,
        )

    def _evaluate_targets(self, payload: dict) -> dict:
        course_refs = parse_course_references(payload.get("course_ids_text", ""))
        criteria = self._normalize_criteria(payload.get("criteria_mode"))
        criteria_config = self._normalize_criteria_config(payload.get("criteria_config"))
        if not course_refs:
            raise ValueError("Selecione pelo menos um grupo ou curso para a busca ativa.")

        client = self.connection_service.build_client(payload)
        items = []
        courses = []
        total_students_found = 0
        total_matched_students = 0
        total_never_accessed_matches = 0
        total_incomplete_matches = 0
        total_inactive_days_matches = 0
        total_low_activity_matches = 0
        courses_without_module_requirements = 0
        analytics_unavailable_courses = 0
        progress_unavailable_courses = 0
        top_priority_course_name = ""
        top_priority_course_ref = ""
        top_priority_score = 0

        for course_ref in course_refs:
            course = client.get_course(course_ref)
            students = self._course_students(client, course)
            total_students_found += len(students)

            analytics_by_user_id = {}
            analytics_available = True
            analytics_error = None
            try:
                analytics_rows = client.list_course_student_summaries(str(course.get("id")))
                analytics_by_user_id = {
                    int(item.get("id")): item
                    for item in analytics_rows
                    if item.get("id") is not None
                }
            except Exception as exc:  # noqa: BLE001
                analytics_available = False
                analytics_error = str(exc)
                analytics_unavailable_courses += 1

            progress_by_user_id = {}
            progress_available = True
            progress_error = None
            try:
                progress_rows = client.get_bulk_user_progress(str(course.get("id")))
                progress_by_user_id = {
                    int(item.get("id")): item.get("progress") or {}
                    for item in progress_rows
                    if item.get("id") is not None
                }
            except Exception as exc:  # noqa: BLE001
                progress_available = False
                progress_error = str(exc)
                progress_unavailable_courses += 1

            enrollments_by_user_id = {}
            enrollment_activity_available = True
            enrollment_error = None
            try:
                enrollment_rows = client.list_course_student_enrollments(str(course.get("id")))
                enrollments_by_user_id = {
                    int(item.get("user_id")): item
                    for item in enrollment_rows
                    if item.get("user_id") is not None
                }
            except Exception as exc:  # noqa: BLE001
                enrollment_activity_available = False
                enrollment_error = str(exc)

            matched_students = 0
            never_accessed_matches = 0
            incomplete_matches = 0
            inactive_days_matches = 0
            low_activity_matches = 0
            course_has_module_requirements = False
            cutoff_dt = self._cutoff_dt(criteria_config.get("inactive_days"))

            for student in students:
                user_id = student.get("id")
                if user_id is None:
                    continue

                analytics_row = analytics_by_user_id.get(int(user_id), {})
                progress_row = progress_by_user_id.get(int(user_id), {})
                enrollment_row = enrollments_by_user_id.get(int(user_id), {})
                page_views = int(analytics_row.get("page_views") or 0)
                participations = int(analytics_row.get("participations") or 0)
                requirement_count = int(progress_row.get("requirement_count") or 0)
                requirement_completed_count = int(progress_row.get("requirement_completed_count") or 0)
                completed_at = progress_row.get("completed_at")
                last_activity_at = enrollment_row.get("last_activity_at")
                total_activity_time = int(enrollment_row.get("total_activity_time") or 0)

                if requirement_count > 0:
                    course_has_module_requirements = True

                has_never_accessed = analytics_available and page_views == 0 and participations == 0
                has_incomplete_resources = (
                    progress_available
                    and requirement_count > 0
                    and requirement_completed_count < requirement_count
                )
                has_inactive_days = self._is_inactive_since(
                    last_activity_at=last_activity_at,
                    cutoff_dt=cutoff_dt,
                    has_never_accessed=has_never_accessed,
                )
                has_low_total_activity = self._has_low_total_activity(
                    total_activity_time=total_activity_time,
                    max_total_activity_minutes=criteria_config.get("max_total_activity_minutes"),
                )

                reasons = []
                if has_never_accessed:
                    reasons.append(self.CRITERIA_NEVER_ACCESSED)
                    never_accessed_matches += 1
                if has_incomplete_resources:
                    reasons.append(self.CRITERIA_INCOMPLETE_RESOURCES)
                    incomplete_matches += 1
                if has_inactive_days:
                    reasons.append("inactive_days")
                    inactive_days_matches += 1
                if has_low_total_activity:
                    reasons.append("low_total_activity")
                    low_activity_matches += 1

                if criteria_config.get("only_with_module_requirements") and not course_has_module_requirements:
                    continue

                if not self._matches_criteria(criteria, reasons, criteria_config):
                    continue

                matched_students += 1
                total_matched_students += 1
                total_never_accessed_matches += 1 if has_never_accessed else 0
                total_incomplete_matches += 1 if has_incomplete_resources else 0
                total_inactive_days_matches += 1 if has_inactive_days else 0
                total_low_activity_matches += 1 if has_low_total_activity else 0
                urgency_score = self._urgency_score(
                    has_never_accessed=has_never_accessed,
                    has_incomplete_resources=has_incomplete_resources,
                    has_inactive_days=has_inactive_days,
                    has_low_total_activity=has_low_total_activity,
                )

                items.append(
                    {
                        "course_ref": course_ref,
                        "course_id": course.get("id"),
                        "course_name": course.get("name"),
                        "user_id": int(user_id),
                        "student_name": self._student_name(student),
                        "page_views": page_views,
                        "participations": participations,
                        "last_activity_at": last_activity_at,
                        "total_activity_time_seconds": total_activity_time,
                        "requirement_count": requirement_count,
                        "requirement_completed_count": requirement_completed_count,
                        "completed_at": completed_at,
                        "reasons": reasons,
                        "reasons_label": self._reasons_label(reasons, criteria_config),
                        "urgency_score": urgency_score,
                        "priority_level": self._priority_level(urgency_score),
                    }
                )

            if not course_has_module_requirements:
                courses_without_module_requirements += 1

            course_urgency_score = self._course_urgency_score(
                students_found=len(students),
                matched_students=matched_students,
                never_accessed_matches=never_accessed_matches,
                incomplete_matches=incomplete_matches,
                inactive_days_matches=inactive_days_matches,
                low_activity_matches=low_activity_matches,
            )
            if course_urgency_score > top_priority_score:
                top_priority_score = course_urgency_score
                top_priority_course_name = course.get("name") or ""
                top_priority_course_ref = course_ref

            courses.append(
                {
                    "course_ref": course_ref,
                    "course_id": course.get("id"),
                    "course_name": course.get("name"),
                    "students_found": len(students),
                    "matched_students": matched_students,
                    "never_accessed_matches": never_accessed_matches,
                    "incomplete_resources_matches": incomplete_matches,
                    "inactive_days_matches": inactive_days_matches,
                    "low_activity_matches": low_activity_matches,
                    "analytics_available": analytics_available,
                    "analytics_error": analytics_error,
                    "progress_available": progress_available,
                    "progress_error": progress_error,
                    "enrollment_activity_available": enrollment_activity_available,
                    "enrollment_error": enrollment_error,
                    "has_module_requirements": course_has_module_requirements,
                    "urgency_score": course_urgency_score,
                    "priority_level": self._priority_level(course_urgency_score),
                    "matched_ratio": round((matched_students / len(students)) * 100, 2) if students else 0,
                }
            )

        return {
            "summary": {
                "criteria_mode": criteria,
                "total_courses": len(courses),
                "total_students_found": total_students_found,
                "total_matched_students": total_matched_students,
                "total_never_accessed_matches": total_never_accessed_matches,
                "total_incomplete_resources_matches": total_incomplete_matches,
                "total_inactive_days_matches": total_inactive_days_matches,
                "total_low_activity_matches": total_low_activity_matches,
                "courses_without_module_requirements": courses_without_module_requirements,
                "analytics_unavailable_courses": analytics_unavailable_courses,
                "progress_unavailable_courses": progress_unavailable_courses,
                "top_priority_course_name": top_priority_course_name,
                "top_priority_course_ref": top_priority_course_ref,
                "top_priority_score": top_priority_score,
                "criteria_config": criteria_config,
            },
            "courses": sorted(
                courses,
                key=lambda item: (
                    -(item.get("urgency_score") or 0),
                    -(item.get("matched_students") or 0),
                    (item.get("course_name") or "").lower(),
                ),
            ),
            "items": sorted(
                items,
                key=lambda item: (
                    -(item.get("urgency_score") or 0),
                    (item.get("course_name") or "").lower(),
                    (item.get("student_name") or "").lower(),
                    item.get("user_id") or 0,
                ),
            ),
        }

    @classmethod
    def _normalize_criteria(cls, raw_value: str | None) -> str:
        value = str(raw_value or cls.CRITERIA_NEVER_OR_INCOMPLETE).strip() or cls.CRITERIA_NEVER_OR_INCOMPLETE
        if value not in cls.VALID_CRITERIA:
            raise ValueError("Criterio de busca ativa invalido.")
        return value

    @classmethod
    def _matches_criteria(cls, criteria: str, reasons: list[str], criteria_config: dict | None = None) -> bool:
        criteria_config = criteria_config or {}
        match_mode = "and" if str(criteria_config.get("match_mode") or "or").strip().lower() == "and" else "or"
        checks = [cls._matches_base_criteria(criteria, reasons)]
        if criteria_config.get("require_never_accessed"):
            checks.append(cls.CRITERIA_NEVER_ACCESSED in reasons)
        if criteria_config.get("require_incomplete_resources"):
            checks.append(cls.CRITERIA_INCOMPLETE_RESOURCES in reasons)
        if criteria_config.get("inactive_days"):
            checks.append("inactive_days" in reasons)
        if criteria_config.get("max_total_activity_minutes") is not None:
            checks.append("low_total_activity" in reasons)
        checks = [item for item in checks if item is not None]
        return all(checks) if match_mode == "and" else any(checks)

    @classmethod
    def _matches_base_criteria(cls, criteria: str, reasons: list[str]) -> bool:
        if criteria == cls.CRITERIA_NEVER_ACCESSED:
            return cls.CRITERIA_NEVER_ACCESSED in reasons
        if criteria == cls.CRITERIA_INCOMPLETE_RESOURCES:
            return cls.CRITERIA_INCOMPLETE_RESOURCES in reasons
        return bool([item for item in reasons if item in {cls.CRITERIA_NEVER_ACCESSED, cls.CRITERIA_INCOMPLETE_RESOURCES}])

    @staticmethod
    def _reasons_label(reasons: list[str], criteria_config: dict | None = None) -> str:
        labels = []
        if "never_accessed" in reasons:
            labels.append("sem acesso nenhum")
        if "incomplete_resources" in reasons:
            labels.append("nao visualizou todos os recursos")
        if "inactive_days" in reasons:
            inactive_days = (criteria_config or {}).get("inactive_days")
            labels.append(f"sem atividade ha {inactive_days} dia(s)" if inactive_days else "sem atividade recente")
        if "low_total_activity" in reasons:
            max_minutes = (criteria_config or {}).get("max_total_activity_minutes")
            labels.append(f"atividade total ate {max_minutes} min" if max_minutes is not None else "atividade total muito baixa")
        return " + ".join(labels) if labels else "-"

    @staticmethod
    def _normalize_criteria_config(raw_config: dict | None) -> dict:
        raw_config = raw_config if isinstance(raw_config, dict) else {}
        match_mode = str(raw_config.get("match_mode") or "or").strip().lower()
        if match_mode not in {"and", "or"}:
            match_mode = "or"
        inactive_days = raw_config.get("inactive_days")
        max_total_activity_minutes = raw_config.get("max_total_activity_minutes")
        return {
            "match_mode": match_mode,
            "inactive_days": int(inactive_days) if str(inactive_days).strip().isdigit() else None,
            "max_total_activity_minutes": int(max_total_activity_minutes) if str(max_total_activity_minutes).strip().isdigit() else None,
            "only_with_module_requirements": bool(raw_config.get("only_with_module_requirements")),
            "require_never_accessed": bool(raw_config.get("require_never_accessed")),
            "require_incomplete_resources": bool(raw_config.get("require_incomplete_resources")),
        }

    @staticmethod
    def _cutoff_dt(inactive_days: int | None) -> datetime | None:
        if inactive_days is None:
            return None
        return datetime.now(UTC) - timedelta(days=max(int(inactive_days), 0))

    @staticmethod
    def _is_inactive_since(*, last_activity_at: str | None, cutoff_dt: datetime | None, has_never_accessed: bool) -> bool:
        if cutoff_dt is None:
            return False
        if not last_activity_at:
            return has_never_accessed
        try:
            parsed = datetime.fromisoformat(str(last_activity_at).replace("Z", "+00:00"))
        except ValueError:
            return False
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed <= cutoff_dt

    @staticmethod
    def _has_low_total_activity(*, total_activity_time: int, max_total_activity_minutes: int | None) -> bool:
        if max_total_activity_minutes is None:
            return False
        return total_activity_time <= max(0, int(max_total_activity_minutes)) * 60

    @staticmethod
    def _urgency_score(
        *,
        has_never_accessed: bool,
        has_incomplete_resources: bool,
        has_inactive_days: bool,
        has_low_total_activity: bool,
    ) -> int:
        score = 0
        if has_never_accessed:
            score += 5
        if has_incomplete_resources:
            score += 3
        if has_inactive_days:
            score += 2
        if has_low_total_activity:
            score += 1
        return score

    @staticmethod
    def _priority_level(score: int) -> str:
        if score >= 8:
            return "critica"
        if score >= 5:
            return "alta"
        if score >= 3:
            return "media"
        return "baixa"

    @staticmethod
    def _course_urgency_score(
        *,
        students_found: int,
        matched_students: int,
        never_accessed_matches: int,
        incomplete_matches: int,
        inactive_days_matches: int,
        low_activity_matches: int,
    ) -> int:
        ratio_bonus = 0
        if students_found:
            ratio = matched_students / students_found
            if ratio >= 0.7:
                ratio_bonus = 4
            elif ratio >= 0.4:
                ratio_bonus = 2
        return (
            (matched_students * 2)
            + (never_accessed_matches * 3)
            + (incomplete_matches * 2)
            + inactive_days_matches
            + low_activity_matches
            + ratio_bonus
        )

    @staticmethod
    def _render_template(template: str, **context: str) -> str:
        rendered = template
        for key, value in context.items():
            rendered = rendered.replace(f"{{{{{key}}}}}", str(value or ""))
        return rendered

    @staticmethod
    def _extract_conversation_ids(response) -> list[int]:
        if isinstance(response, list):
            return [item.get("id") for item in response if item.get("id") is not None]
        if isinstance(response, dict) and response.get("id") is not None:
            return [response["id"]]
        return []

    def _write_report(self, job_id: str, rows: list[dict]) -> str:
        report_filename = f"engagement-report-{job_id}.csv"
        report_path = Path(self.app_config.reports_dir) / report_filename
        fieldnames = [
            "course_ref",
            "course_id",
            "course_name",
            "user_id",
            "student_name",
            "page_views",
            "participations",
            "last_activity_at",
            "total_activity_time_seconds",
            "requirement_count",
            "requirement_completed_count",
            "completed_at",
            "reasons",
            "sent",
            "dry_run",
            "conversation_id",
            "error",
        ]

        with report_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return report_filename

    @staticmethod
    def _student_name(student: dict) -> str:
        return (
            student.get("name")
            or student.get("short_name")
            or student.get("sortable_name")
            or f"Usuario {student.get('id')}"
        )

    @staticmethod
    def _course_students(client, course: dict) -> list[dict]:
        return [
            student
            for student in client.list_course_students(str(course.get("id")))
            if not student.get("is_test_student")
        ]
