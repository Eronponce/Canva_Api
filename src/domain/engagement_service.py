from __future__ import annotations

import csv
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
                "never_accessed_matches": course["never_accessed_matches"],
                "incomplete_resources_matches": course["incomplete_resources_matches"],
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
        if not course_refs:
            raise ValueError("Selecione pelo menos um grupo ou curso para a busca ativa.")

        client = self.connection_service.build_client(payload)
        items = []
        courses = []
        total_students_found = 0
        total_matched_students = 0
        total_never_accessed_matches = 0
        total_incomplete_matches = 0
        courses_without_module_requirements = 0
        analytics_unavailable_courses = 0
        progress_unavailable_courses = 0

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

            matched_students = 0
            never_accessed_matches = 0
            incomplete_matches = 0
            course_has_module_requirements = False

            for student in students:
                user_id = student.get("id")
                if user_id is None:
                    continue

                analytics_row = analytics_by_user_id.get(int(user_id), {})
                progress_row = progress_by_user_id.get(int(user_id), {})
                page_views = int(analytics_row.get("page_views") or 0)
                participations = int(analytics_row.get("participations") or 0)
                requirement_count = int(progress_row.get("requirement_count") or 0)
                requirement_completed_count = int(progress_row.get("requirement_completed_count") or 0)
                completed_at = progress_row.get("completed_at")

                if requirement_count > 0:
                    course_has_module_requirements = True

                has_never_accessed = analytics_available and page_views == 0 and participations == 0
                has_incomplete_resources = (
                    progress_available
                    and requirement_count > 0
                    and requirement_completed_count < requirement_count
                )

                reasons = []
                if has_never_accessed:
                    reasons.append(self.CRITERIA_NEVER_ACCESSED)
                    never_accessed_matches += 1
                if has_incomplete_resources:
                    reasons.append(self.CRITERIA_INCOMPLETE_RESOURCES)
                    incomplete_matches += 1

                if not self._matches_criteria(criteria, reasons):
                    continue

                matched_students += 1
                total_matched_students += 1
                total_never_accessed_matches += 1 if has_never_accessed else 0
                total_incomplete_matches += 1 if has_incomplete_resources else 0

                items.append(
                    {
                        "course_ref": course_ref,
                        "course_id": course.get("id"),
                        "course_name": course.get("name"),
                        "user_id": int(user_id),
                        "student_name": self._student_name(student),
                        "page_views": page_views,
                        "participations": participations,
                        "requirement_count": requirement_count,
                        "requirement_completed_count": requirement_completed_count,
                        "completed_at": completed_at,
                        "reasons": reasons,
                        "reasons_label": self._reasons_label(reasons),
                    }
                )

            if not course_has_module_requirements:
                courses_without_module_requirements += 1

            courses.append(
                {
                    "course_ref": course_ref,
                    "course_id": course.get("id"),
                    "course_name": course.get("name"),
                    "students_found": len(students),
                    "matched_students": matched_students,
                    "never_accessed_matches": never_accessed_matches,
                    "incomplete_resources_matches": incomplete_matches,
                    "analytics_available": analytics_available,
                    "analytics_error": analytics_error,
                    "progress_available": progress_available,
                    "progress_error": progress_error,
                    "has_module_requirements": course_has_module_requirements,
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
                "courses_without_module_requirements": courses_without_module_requirements,
                "analytics_unavailable_courses": analytics_unavailable_courses,
                "progress_unavailable_courses": progress_unavailable_courses,
            },
            "courses": courses,
            "items": sorted(
                items,
                key=lambda item: (
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
    def _matches_criteria(cls, criteria: str, reasons: list[str]) -> bool:
        if criteria == cls.CRITERIA_NEVER_ACCESSED:
            return cls.CRITERIA_NEVER_ACCESSED in reasons
        if criteria == cls.CRITERIA_INCOMPLETE_RESOURCES:
            return cls.CRITERIA_INCOMPLETE_RESOURCES in reasons
        return bool(reasons)

    @staticmethod
    def _reasons_label(reasons: list[str]) -> str:
        labels = []
        if "never_accessed" in reasons:
            labels.append("sem acesso nenhum")
        if "incomplete_resources" in reasons:
            labels.append("nao visualizou todos os recursos")
        return " + ".join(labels) if labels else "-"

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
