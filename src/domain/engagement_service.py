from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from src.services.canvas_client import CanvasApiError
from src.utils.parsing import parse_course_references
from src.utils.time_utils import utc_now_iso


class EngagementService:
    CRITERIA_MISSING_ASSIGNMENT = "missing_assignment"
    CRITERIA_MISSING_QUIZ = "missing_quiz"
    CRITERIA_NEVER_ACCESSED = "never_accessed"
    CRITERIA_LOW_TOTAL_ACTIVITY = "low_total_activity"
    CRITERIA_MISSING_ACTIVITY = "missing_activity"
    CRITERIA_INCOMPLETE_RESOURCES = "incomplete_resources"
    CRITERIA_NEVER_OR_INCOMPLETE = "never_accessed_or_incomplete_resources"
    VALID_CRITERIA = {
        CRITERIA_MISSING_ASSIGNMENT,
        CRITERIA_MISSING_QUIZ,
        CRITERIA_NEVER_ACCESSED,
        CRITERIA_LOW_TOTAL_ACTIVITY,
    }
    LEGACY_CRITERIA_ALIASES = {
        CRITERIA_MISSING_ACTIVITY: CRITERIA_MISSING_ASSIGNMENT,
        CRITERIA_INCOMPLETE_RESOURCES: CRITERIA_NEVER_ACCESSED,
        CRITERIA_NEVER_OR_INCOMPLETE: CRITERIA_NEVER_ACCESSED,
    }
    DEFAULT_CRITERIA = (CRITERIA_NEVER_ACCESSED, CRITERIA_LOW_TOTAL_ACTIVITY)
    INACTIVITY_CRITERIA = {CRITERIA_NEVER_ACCESSED, CRITERIA_LOW_TOTAL_ACTIVITY}
    ACTIVITY_CRITERIA = {CRITERIA_MISSING_ASSIGNMENT, CRITERIA_MISSING_QUIZ}
    MESSAGE_KIND_INACTIVITY = "inactivity"
    MESSAGE_KIND_ACTIVITY = "missing_activity"
    EVALUATED_ASSIGNMENT_SUBMISSION_TYPES = {
        "external_tool",
        "online_text_entry",
        "online_upload",
        "online_url",
        "media_recording",
        "student_annotation",
    }
    NON_EVALUATED_ASSIGNMENT_SUBMISSION_TYPES = {
        "none",
        "not_graded",
        "on_paper",
        "online_quiz",
    }
    GRADED_QUIZ_TYPES = {"assignment", "graded_survey"}
    NON_EVALUATED_QUIZ_TYPES = {"practice_quiz", "survey"}

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
            "analysis": evaluation["analysis"],
        }

    def complete_preview_report(self, job_id: str, payload: dict, preview_result: dict) -> dict | None:
        criteria_modes = self._normalize_criteria_modes(payload)
        criteria = self._criteria_strategy_label(criteria_modes)
        self.job_manager.mark_running(job_id, total=1, step="Gerando CSV de conferencia de inativos")

        csv_rows = [
            self._csv_row_from_analysis_student(student)
            for student in (preview_result.get("analysis") or {}).get("student_rows", [])
        ]
        report_filename = self._write_report(job_id, csv_rows, prefix="engagement-preview-report")
        course_rows = [
            self._preview_course_result_row(course, criteria)
            for course in preview_result.get("courses") or []
        ]
        summary = dict(preview_result.get("summary") or {})
        summary.update(
            {
                "preview_only": True,
                "requested_at": utc_now_iso(),
                "criteria_mode": criteria,
                "criteria_modes": criteria_modes,
                "dry_run": True,
                "requested_strategy": criteria,
                "effective_strategy": "preview_only",
                "total_recipients_targeted": int(summary.get("total_target_messages") or 0),
                "total_recipients_sent": 0,
            }
        )
        self.job_manager.add_log(
            job_id,
            level="info",
            message="CSV de conferencia de inativos gerado.",
            data={
                "criteria_modes": criteria_modes,
                "courses_selected": len(preview_result.get("courses") or []),
                "messages_targeted": len(preview_result.get("items") or []),
            },
        )
        self.job_manager.complete(
            job_id,
            result={
                "summary": summary,
                "course_results": course_rows,
                "analysis": preview_result.get("analysis") or {},
            },
            report_filename=report_filename,
        )
        return self.job_manager.get_job(job_id)

    def run_job(self, job_id: str, payload: dict) -> None:
        course_refs = parse_course_references(payload.get("course_ids_text", ""))
        criteria_modes = self._normalize_criteria_modes(payload)
        criteria = self._criteria_strategy_label(criteria_modes)
        inactivity_subject_template = (payload.get("inactivity_subject") or payload.get("subject") or "").strip()
        inactivity_body_template = (payload.get("inactivity_message") or payload.get("message") or "").strip()
        activity_subject_template = (payload.get("activity_subject") or payload.get("subject") or "").strip()
        activity_body_template = (payload.get("activity_message") or payload.get("message") or "").strip()
        dry_run = bool(payload.get("dry_run"))

        if not course_refs:
            raise ValueError("Selecione pelo menos um grupo ou curso para a busca ativa.")
        if self._has_inactivity_criteria(criteria_modes):
            if not inactivity_subject_template:
                raise ValueError("Informe o assunto da mensagem de inatividade.")
            if not inactivity_body_template:
                raise ValueError("Informe o corpo da mensagem de inatividade.")
        if self._has_activity_criteria(criteria_modes):
            if not activity_subject_template:
                raise ValueError("Informe o assunto da mensagem de atividade pendente.")
            if not activity_body_template:
                raise ValueError("Informe o corpo da mensagem de atividade pendente.")

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
                "criteria_modes": criteria_modes,
                "courses_selected": len(evaluation["courses"]),
                "messages_targeted": len(items),
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
                "inactivity_messages": course.get("inactivity_messages", 0),
                "activity_messages": course.get("activity_messages", 0),
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
                "missing_activity_matches": course.get("missing_activity_matches", 0),
                "missing_assignment_matches": course.get("missing_assignment_matches", 0),
                "missing_quiz_matches": course.get("missing_quiz_matches", 0),
                "activity_count": course.get("activity_count", 0),
                "activity_kind": course.get("activity_kind"),
                "activity_filter_available": course.get("activity_filter_available"),
                "activity_filter_error": course.get("activity_filter_error"),
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
                    step=f"Enviando {item['message_kind_label']} para {item['student_name']} em {course['course_name']}",
                )
                if item.get("message_kind") == self.MESSAGE_KIND_ACTIVITY:
                    subject_template = activity_subject_template
                    body_template = activity_body_template
                else:
                    subject_template = inactivity_subject_template
                    body_template = inactivity_body_template

                rendered_subject = self._render_template(
                    subject_template,
                    student_name=item["student_name"],
                    course_name=course["course_name"],
                    course_ref=course["course_ref"],
                    reason=item["reasons_label"],
                    missing_activities=item.get("missing_activities_label", ""),
                    activity_type=item.get("activity_type_label", ""),
                )
                rendered_body = self._render_template(
                    body_template,
                    student_name=item["student_name"],
                    course_name=course["course_name"],
                    course_ref=course["course_ref"],
                    reason=item["reasons_label"],
                    missing_activities=item.get("missing_activities_label", ""),
                    activity_type=item.get("activity_type_label", ""),
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
                    self._csv_row_from_item(
                        item,
                        sent=sent,
                        dry_run=dry_run,
                        conversation_id=conversation_id,
                        error=send_error or "",
                    )
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
                "criteria_modes": criteria_modes,
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
                "analysis": evaluation["analysis"],
            },
            report_filename=report_filename,
        )

    def _evaluate_targets(self, payload: dict) -> dict:
        course_refs = parse_course_references(payload.get("course_ids_text", ""))
        criteria_modes = self._normalize_criteria_modes(payload)
        criteria = self._criteria_strategy_label(criteria_modes)
        criteria_config = self._normalize_criteria_config(payload.get("criteria_config"))
        self._validate_criteria_config(criteria_modes, criteria_config)
        if not course_refs:
            raise ValueError("Selecione pelo menos um grupo ou curso para a busca ativa.")

        client = self.connection_service.build_client(payload)
        items = []
        courses = []
        analyzed_students: dict[int, dict] = {}
        total_students_found = 0
        total_unique_students_matched = 0
        total_matched_students = 0
        total_never_accessed_matches = 0
        total_low_activity_matches = 0
        total_missing_activity_matches = 0
        total_missing_assignment_matches = 0
        total_missing_quiz_matches = 0
        total_activities_checked = 0
        analytics_unavailable_courses = 0
        progress_unavailable_courses = 0
        enrollment_activity_unavailable_courses = 0
        activity_unavailable_courses = 0
        top_priority_course_name = ""
        top_priority_course_ref = ""
        top_priority_score = 0
        needs_analytics = self.CRITERIA_NEVER_ACCESSED in criteria_modes
        needs_enrollment_activity = self.CRITERIA_LOW_TOTAL_ACTIVITY in criteria_modes
        needs_assignments = self.CRITERIA_MISSING_ASSIGNMENT in criteria_modes
        needs_quizzes = self.CRITERIA_MISSING_QUIZ in criteria_modes

        for course_ref in course_refs:
            course = client.get_course(course_ref)
            students = self._course_students(client, course)
            total_students_found += len(students)

            analytics_by_user_id = {}
            analytics_available = True
            analytics_error = None
            if needs_analytics:
                try:
                    analytics_by_user_id = self._analytics_by_user_id(
                        client.list_course_student_summaries(str(course.get("id")))
                    )
                except Exception as exc:  # noqa: BLE001
                    analytics_available = False
                    analytics_error = str(exc)
                    analytics_unavailable_courses += 1

            enrollments_by_user_id = {}
            enrollment_activity_available = True
            enrollment_error = None
            if needs_enrollment_activity:
                try:
                    enrollments_by_user_id = self._enrollments_by_user_id(
                        client.list_course_student_enrollments(str(course.get("id")))
                    )
                except Exception as exc:  # noqa: BLE001
                    enrollment_activity_available = False
                    enrollment_error = str(exc)
                    enrollment_activity_unavailable_courses += 1

            assignment_status = self._empty_activity_status("assignment")
            quiz_status = self._empty_activity_status("quiz")
            if needs_assignments:
                assignment_status = self._load_course_activity_status(client, str(course.get("id")), "assignment")
                if not assignment_status["available"]:
                    activity_unavailable_courses += 1
            if needs_quizzes:
                quiz_status = self._load_course_activity_status(client, str(course.get("id")), "quiz")
                if not quiz_status["available"]:
                    activity_unavailable_courses += 1

            activity_count = int(assignment_status["activity_count"]) + int(quiz_status["activity_count"])
            total_activities_checked += activity_count

            matched_user_ids = set()
            matched_messages = 0
            inactivity_messages = 0
            activity_messages = 0
            never_accessed_matches = 0
            low_activity_matches = 0
            missing_activity_matches = 0
            missing_assignment_matches = 0
            missing_quiz_matches = 0

            for student in students:
                user_id = student.get("id")
                if user_id is None:
                    continue
                int_user_id = int(user_id)
                student_rollup = analyzed_students.setdefault(
                    int_user_id,
                    self._new_analysis_student(student),
                )
                student_rollup["course_refs"].add(course_ref)
                student_rollup["course_names"].add(course.get("name") or course_ref)
                analytics = analytics_by_user_id.get(int_user_id, {})
                enrollment = enrollments_by_user_id.get(int_user_id, {})

                inactivity_reasons = []
                has_never_accessed = (
                    needs_analytics
                    and analytics_available
                    and self._has_never_accessed(analytics)
                )
                has_low_activity = (
                    needs_enrollment_activity
                    and enrollment_activity_available
                    and self._has_low_total_activity(enrollment, criteria_config["max_total_activity_minutes"])
                )
                if has_never_accessed:
                    student_rollup["never_accessed"] = True
                    inactivity_reasons.append(self.CRITERIA_NEVER_ACCESSED)
                    never_accessed_matches += 1
                    total_never_accessed_matches += 1
                if has_low_activity:
                    student_rollup["low_activity"] = True
                    inactivity_reasons.append(self.CRITERIA_LOW_TOTAL_ACTIVITY)
                    low_activity_matches += 1
                    total_low_activity_matches += 1

                if inactivity_reasons:
                    student_rollup["message_kinds"].add(self.MESSAGE_KIND_INACTIVITY)
                    urgency_score = self._urgency_score(
                        has_never_accessed=has_never_accessed,
                        has_low_activity=has_low_activity,
                        has_missing_activity=False,
                    )
                    matched_user_ids.add(int_user_id)
                    matched_messages += 1
                    inactivity_messages += 1
                    total_matched_students += 1
                    items.append(
                        {
                            **self._student_item_base(course_ref, course, student),
                            "message_kind": self.MESSAGE_KIND_INACTIVITY,
                            "message_kind_label": "Inatividade",
                            "page_views": int(analytics.get("page_views") or 0),
                            "participations": int(analytics.get("participations") or 0),
                            "last_activity_at": enrollment.get("last_activity_at"),
                            "total_activity_time_seconds": int(enrollment.get("total_activity_time") or 0),
                            "requirement_count": 0,
                            "requirement_completed_count": 0,
                            "completed_at": None,
                            "activity_type": None,
                            "activity_type_label": "",
                            "activity_id": None,
                            "activity_submitted": None,
                            "activity_count": 0,
                            "activity_submitted_count": 0,
                            "activity_missing_count": 0,
                            "missing_activity_names": [],
                            "missing_assignment_names": [],
                            "missing_quiz_names": [],
                            "missing_activities_label": "",
                            "reasons": inactivity_reasons,
                            "reasons_label": self._reasons_label(inactivity_reasons, criteria_config),
                            "urgency_score": urgency_score,
                            "priority_level": self._priority_level(urgency_score),
                        }
                    )

                assignment_missing_rows = self._missing_activity_rows_for_user(assignment_status, int_user_id)
                quiz_missing_rows = self._missing_activity_rows_for_user(quiz_status, int_user_id)
                activity_reasons = []
                if assignment_missing_rows:
                    student_rollup["missing_assignment"] = True
                    student_rollup["missing_assignment_names"].update(
                        activity["name"] for activity in assignment_missing_rows
                    )
                    activity_reasons.append(self.CRITERIA_MISSING_ASSIGNMENT)
                    missing_assignment_matches += 1
                    total_missing_assignment_matches += 1
                if quiz_missing_rows:
                    student_rollup["missing_quiz"] = True
                    student_rollup["missing_quiz_names"].update(
                        activity["name"] for activity in quiz_missing_rows
                    )
                    activity_reasons.append(self.CRITERIA_MISSING_QUIZ)
                    missing_quiz_matches += 1
                    total_missing_quiz_matches += 1

                if activity_reasons:
                    student_rollup["message_kinds"].add(self.MESSAGE_KIND_ACTIVITY)
                    all_missing_rows = assignment_missing_rows + quiz_missing_rows
                    submitted_activity_count = (
                        int(assignment_status["activity_count"])
                        + int(quiz_status["activity_count"])
                        - len(all_missing_rows)
                    )
                    has_missing_activity = bool(all_missing_rows)
                    urgency_score = self._urgency_score(
                        has_never_accessed=False,
                        has_low_activity=False,
                        has_missing_activity=has_missing_activity,
                    )
                    matched_user_ids.add(int_user_id)
                    matched_messages += 1
                    activity_messages += 1
                    missing_activity_matches += 1
                    total_missing_activity_matches += 1
                    total_matched_students += 1
                    activity_type = self._combined_activity_type(activity_reasons)
                    items.append(
                        {
                            **self._student_item_base(course_ref, course, student),
                            "message_kind": self.MESSAGE_KIND_ACTIVITY,
                            "message_kind_label": "Atividade pendente",
                            "page_views": int(analytics.get("page_views") or 0),
                            "participations": int(analytics.get("participations") or 0),
                            "last_activity_at": enrollment.get("last_activity_at"),
                            "total_activity_time_seconds": int(enrollment.get("total_activity_time") or 0),
                            "requirement_count": 0,
                            "requirement_completed_count": 0,
                            "completed_at": None,
                            "activity_type": activity_type,
                            "activity_type_label": self._activity_type_label(activity_type),
                            "activity_id": all_missing_rows[0]["id"] if all_missing_rows else None,
                            "activity_submitted": not bool(all_missing_rows),
                            "activity_count": int(assignment_status["activity_count"]) + int(quiz_status["activity_count"]),
                            "activity_submitted_count": submitted_activity_count,
                            "activity_missing_count": len(all_missing_rows),
                            "missing_activity_names": [activity["name"] for activity in all_missing_rows],
                            "missing_assignment_names": [activity["name"] for activity in assignment_missing_rows],
                            "missing_quiz_names": [activity["name"] for activity in quiz_missing_rows],
                            "missing_activities_label": self._missing_activities_label(assignment_missing_rows, quiz_missing_rows),
                            "reasons": activity_reasons,
                            "reasons_label": self._reasons_label(activity_reasons, criteria_config),
                            "urgency_score": urgency_score,
                            "priority_level": self._priority_level(urgency_score),
                        }
                    )

            total_unique_students_matched += len(matched_user_ids)

            course_urgency_score = self._course_urgency_score(
                students_found=len(students),
                matched_students=len(matched_user_ids),
                missing_activity_matches=missing_activity_matches,
                never_accessed_matches=never_accessed_matches,
                low_activity_matches=low_activity_matches,
            )
            if course_urgency_score > top_priority_score:
                top_priority_score = course_urgency_score
                top_priority_course_name = course.get("name") or ""
                top_priority_course_ref = course_ref

            course_activity_filter_error = self._combined_activity_error(assignment_status, quiz_status)
            courses.append(
                {
                    "course_ref": course_ref,
                    "course_id": course.get("id"),
                    "course_name": course.get("name"),
                    "students_found": len(students),
                    "matched_students": len(matched_user_ids),
                    "target_messages": matched_messages,
                    "inactivity_messages": inactivity_messages,
                    "activity_messages": activity_messages,
                    "never_accessed_matches": never_accessed_matches,
                    "incomplete_resources_matches": 0,
                    "inactive_days_matches": 0,
                    "low_activity_matches": low_activity_matches,
                    "missing_activity_matches": missing_activity_matches,
                    "missing_assignment_matches": missing_assignment_matches,
                    "missing_quiz_matches": missing_quiz_matches,
                    "activity_count": activity_count,
                    "assignment_count": assignment_status["activity_count"],
                    "quiz_count": quiz_status["activity_count"],
                    "activity_kind": self._course_activity_kind(needs_assignments, needs_quizzes),
                    "analytics_available": analytics_available,
                    "analytics_error": analytics_error,
                    "progress_available": True,
                    "progress_error": None,
                    "enrollment_activity_available": enrollment_activity_available,
                    "enrollment_error": enrollment_error,
                    "activity_filter_available": not course_activity_filter_error,
                    "activity_filter_error": course_activity_filter_error,
                    "activity_filter_applies": needs_assignments or needs_quizzes,
                    "has_module_requirements": False,
                    "urgency_score": course_urgency_score,
                    "priority_level": self._priority_level(course_urgency_score),
                    "matched_ratio": round((len(matched_user_ids) / len(students)) * 100, 2) if students else 0,
                }
            )

        analysis = self._build_analysis(
            analyzed_students=analyzed_students,
            courses=courses,
            criteria_config=criteria_config,
        )

        return {
            "summary": {
                "criteria_mode": criteria,
                "criteria_modes": criteria_modes,
                "total_courses": len(courses),
                "total_students_found": total_students_found,
                "total_unique_students_matched": total_unique_students_matched,
                "total_matched_students": total_matched_students,
                "total_target_messages": total_matched_students,
                "total_inactivity_messages": sum(course.get("inactivity_messages", 0) for course in courses),
                "total_activity_messages": sum(course.get("activity_messages", 0) for course in courses),
                "total_never_accessed_matches": total_never_accessed_matches,
                "total_incomplete_resources_matches": 0,
                "total_inactive_days_matches": 0,
                "total_low_activity_matches": total_low_activity_matches,
                "total_missing_activity_matches": total_missing_activity_matches,
                "total_missing_assignment_matches": total_missing_assignment_matches,
                "total_missing_quiz_matches": total_missing_quiz_matches,
                "total_activities_checked": total_activities_checked,
                "courses_without_module_requirements": 0,
                "analytics_unavailable_courses": analytics_unavailable_courses,
                "progress_unavailable_courses": progress_unavailable_courses,
                "enrollment_activity_unavailable_courses": enrollment_activity_unavailable_courses,
                "activity_unavailable_courses": activity_unavailable_courses,
                "activity_filter_mismatched_courses": 0,
                "top_priority_course_name": top_priority_course_name,
                "top_priority_course_ref": top_priority_course_ref,
                "top_priority_score": top_priority_score,
                "criteria_config": criteria_config,
            },
            "courses": sorted(
                courses,
                key=lambda item: (
                    -(item.get("urgency_score") or 0),
                    -(item.get("target_messages") or 0),
                    (item.get("course_name") or "").lower(),
                ),
            ),
            "items": sorted(
                items,
                key=lambda item: (
                    -(item.get("urgency_score") or 0),
                    (item.get("course_name") or "").lower(),
                    (item.get("student_name") or "").lower(),
                    item.get("message_kind") or "",
                    item.get("user_id") or 0,
                ),
            ),
            "analysis": analysis,
        }

    @staticmethod
    def _new_analysis_student(student: dict) -> dict:
        return {
            "user_id": int(student.get("id")),
            "student_name": EngagementService._student_name(student),
            "course_refs": set(),
            "course_names": set(),
            "message_kinds": set(),
            "never_accessed": False,
            "low_activity": False,
            "missing_quiz": False,
            "missing_assignment": False,
            "missing_quiz_names": set(),
            "missing_assignment_names": set(),
        }

    @classmethod
    def _build_analysis(cls, *, analyzed_students: dict[int, dict], courses: list[dict], criteria_config: dict) -> dict:
        student_rows = []
        total_never_accessed = 0
        total_low_activity = 0
        total_missing_quiz = 0
        total_missing_assignment = 0
        total_targeted = 0
        total_clear = 0

        for student in analyzed_students.values():
            never_accessed = bool(student["never_accessed"])
            low_activity = bool(student["low_activity"])
            missing_quiz = bool(student["missing_quiz"])
            missing_assignment = bool(student["missing_assignment"])
            is_targeted = bool(student["message_kinds"])
            is_clear = not any((never_accessed, low_activity, missing_quiz, missing_assignment))

            if never_accessed:
                total_never_accessed += 1
            if low_activity:
                total_low_activity += 1
            if missing_quiz:
                total_missing_quiz += 1
            if missing_assignment:
                total_missing_assignment += 1
            if is_targeted:
                total_targeted += 1
            if is_clear:
                total_clear += 1

            missing_quiz_names = sorted(student["missing_quiz_names"])
            missing_assignment_names = sorted(student["missing_assignment_names"])
            message_kind_labels = []
            if cls.MESSAGE_KIND_INACTIVITY in student["message_kinds"]:
                message_kind_labels.append("Inatividade")
            if cls.MESSAGE_KIND_ACTIVITY in student["message_kinds"]:
                message_kind_labels.append("Pendencia")

            student_rows.append(
                {
                    "user_id": student["user_id"],
                    "student_name": student["student_name"],
                    "course_count": len(student["course_refs"]),
                    "course_refs": sorted(student["course_refs"]),
                    "course_names": sorted(student["course_names"]),
                    "courses_label": " | ".join(sorted(student["course_names"])),
                    "never_accessed": never_accessed,
                    "low_activity": low_activity,
                    "missing_quiz": missing_quiz,
                    "missing_assignment": missing_assignment,
                    "targeted": is_targeted,
                    "clear": is_clear,
                    "message_kind_count": len(student["message_kinds"]),
                    "message_kind_labels": message_kind_labels,
                    "missing_quiz_names": missing_quiz_names,
                    "missing_assignment_names": missing_assignment_names,
                    "missing_activity_names": missing_quiz_names + missing_assignment_names,
                }
            )

        student_rows.sort(
            key=lambda item: (
                item["clear"],
                -item["message_kind_count"],
                -(1 if item["never_accessed"] else 0),
                -(1 if item["low_activity"] else 0),
                -(1 if item["missing_quiz"] else 0),
                -(1 if item["missing_assignment"] else 0),
                item["student_name"].lower(),
            )
        )

        total_students = len(student_rows)
        course_rows = []
        for course in courses:
            students_found = int(course.get("students_found") or 0)
            course_rows.append(
                {
                    "course_ref": course.get("course_ref"),
                    "course_name": course.get("course_name"),
                    "students_found": students_found,
                    "students_clear": max(students_found - int(course.get("matched_students") or 0), 0),
                    "targeted_students": int(course.get("matched_students") or 0),
                    "never_accessed_students": int(course.get("never_accessed_matches") or 0),
                    "low_activity_students": int(course.get("low_activity_matches") or 0),
                    "missing_quiz_students": int(course.get("missing_quiz_matches") or 0),
                    "missing_assignment_students": int(course.get("missing_assignment_matches") or 0),
                    "objective_count": int(course.get("quiz_count") or 0),
                    "integrated_count": int(course.get("assignment_count") or 0),
                    "clear_pct": cls._percent(max(students_found - int(course.get("matched_students") or 0), 0), students_found),
                    "targeted_pct": cls._percent(int(course.get("matched_students") or 0), students_found),
                    "never_accessed_pct": cls._percent(int(course.get("never_accessed_matches") or 0), students_found),
                    "low_activity_pct": cls._percent(int(course.get("low_activity_matches") or 0), students_found),
                    "missing_quiz_pct": cls._percent(int(course.get("missing_quiz_matches") or 0), students_found),
                    "missing_assignment_pct": cls._percent(int(course.get("missing_assignment_matches") or 0), students_found),
                    "objective_done_pct": cls._percent(students_found - int(course.get("missing_quiz_matches") or 0), students_found) if int(course.get("quiz_count") or 0) else None,
                    "integrated_done_pct": cls._percent(students_found - int(course.get("missing_assignment_matches") or 0), students_found) if int(course.get("assignment_count") or 0) else None,
                }
            )

        issue_distribution = [
            {"key": "clear", "label": "Fez tudo", "count": total_clear, "pct": cls._percent(total_clear, total_students)},
            {"key": "never_accessed", "label": "Nunca entrou", "count": total_never_accessed, "pct": cls._percent(total_never_accessed, total_students)},
            {"key": "low_activity", "label": f"Menos de {criteria_config.get('max_total_activity_minutes', 0):g} min", "count": total_low_activity, "pct": cls._percent(total_low_activity, total_students)},
            {"key": "missing_quiz", "label": "Nao realizou atividade objetiva", "count": total_missing_quiz, "pct": cls._percent(total_missing_quiz, total_students)},
            {"key": "missing_assignment", "label": "Nao realizou atividade integradora", "count": total_missing_assignment, "pct": cls._percent(total_missing_assignment, total_students)},
        ]

        return {
            "summary": {
                "total_unique_students": total_students,
                "targeted_unique_students": total_targeted,
                "clear_unique_students": total_clear,
                "never_accessed_unique_students": total_never_accessed,
                "low_activity_unique_students": total_low_activity,
                "missing_quiz_unique_students": total_missing_quiz,
                "missing_assignment_unique_students": total_missing_assignment,
                "clear_pct": cls._percent(total_clear, total_students),
                "targeted_pct": cls._percent(total_targeted, total_students),
                "never_accessed_pct": cls._percent(total_never_accessed, total_students),
                "low_activity_pct": cls._percent(total_low_activity, total_students),
                "missing_quiz_pct": cls._percent(total_missing_quiz, total_students),
                "missing_assignment_pct": cls._percent(total_missing_assignment, total_students),
                "minutes_threshold": criteria_config.get("max_total_activity_minutes", 0),
            },
            "issue_distribution": issue_distribution,
            "course_rows": sorted(course_rows, key=lambda item: (-(item.get("targeted_pct") or 0), item.get("course_name") or "")),
            "student_rows": student_rows,
        }

    @staticmethod
    def _percent(part: int | float, total: int | float) -> float:
        if not total:
            return 0.0
        return round((float(part) / float(total)) * 100, 2)

    @classmethod
    def _normalize_criteria(cls, raw_value: str | None) -> str:
        value = str(raw_value or cls.CRITERIA_NEVER_ACCESSED).strip() or cls.CRITERIA_NEVER_ACCESSED
        value = cls.LEGACY_CRITERIA_ALIASES.get(value, value)
        if value not in cls.VALID_CRITERIA:
            raise ValueError("Criterio de busca ativa invalido.")
        return value

    @classmethod
    def _normalize_criteria_modes(cls, payload: dict) -> list[str]:
        raw_config = payload.get("criteria_config") if isinstance(payload.get("criteria_config"), dict) else {}
        raw_modes = payload.get("criteria_modes") or raw_config.get("criteria_modes") or raw_config.get("selected_criteria")
        if raw_modes is None:
            raw_modes = payload.get("criteria_mode")
        if raw_modes is None:
            raw_modes = cls.DEFAULT_CRITERIA
        if isinstance(raw_modes, str):
            raw_modes = [part.strip() for part in raw_modes.split(",") if part.strip()]
        normalized = []
        for raw_mode in raw_modes:
            value = cls._normalize_criteria(str(raw_mode))
            if value not in normalized:
                normalized.append(value)
        if not normalized:
            raise ValueError("Selecione pelo menos um criterio de busca ativa.")
        return normalized

    @classmethod
    def _criteria_strategy_label(cls, criteria_modes: list[str]) -> str:
        return ",".join(criteria_modes)

    @classmethod
    def _has_inactivity_criteria(cls, criteria_modes: list[str]) -> bool:
        return any(criteria in cls.INACTIVITY_CRITERIA for criteria in criteria_modes)

    @classmethod
    def _has_activity_criteria(cls, criteria_modes: list[str]) -> bool:
        return any(criteria in cls.ACTIVITY_CRITERIA for criteria in criteria_modes)

    @staticmethod
    def _reasons_label(reasons: list[str], criteria_config: dict | None = None) -> str:
        labels = []
        if "never_accessed" in reasons:
            labels.append("nunca entrou")
        if "low_total_activity" in reasons:
            max_minutes = (criteria_config or {}).get("max_total_activity_minutes")
            labels.append(f"menos de {max_minutes:g} min" if isinstance(max_minutes, (int, float)) else "poucos minutos")
        if "missing_quiz" in reasons:
            labels.append("nao realizou a atividade objetiva")
        if "missing_assignment" in reasons:
            labels.append("nao realizou a atividade integradora")
        return " + ".join(labels) if labels else "-"

    @classmethod
    def _normalize_criteria_config(cls, raw_config: dict | None) -> dict:
        raw_config = raw_config or {}
        try:
            max_minutes = float(raw_config.get("max_total_activity_minutes", 10))
        except (TypeError, ValueError):
            max_minutes = 10.0
        return {
            "max_total_activity_minutes": max_minutes,
        }

    @classmethod
    def _validate_criteria_config(cls, criteria_modes: list[str], criteria_config: dict) -> None:
        if cls.CRITERIA_LOW_TOTAL_ACTIVITY in criteria_modes and criteria_config.get("max_total_activity_minutes", 0) <= 0:
            raise ValueError("Informe uma quantidade de minutos maior que zero.")

    @staticmethod
    def _criteria_activity_type(criteria: str) -> str:
        return "quiz" if criteria == EngagementService.CRITERIA_MISSING_QUIZ else "assignment"

    @staticmethod
    def _no_activity_label(activity_type: str) -> str:
        return "Nenhuma atividade objetiva publicada encontrada na disciplina." if activity_type == "quiz" else "Nenhuma atividade integradora publicada encontrada na disciplina."

    @classmethod
    def _empty_activity_status(cls, activity_type: str) -> dict:
        return {
            "activity_type": activity_type,
            "activity_rows": [],
            "submitted_activity_ids_by_user_id": defaultdict(set),
            "available": True,
            "error": None,
            "activity_count": 0,
        }

    @classmethod
    def _load_course_activity_status(cls, client, course_id: str, activity_type: str) -> dict:
        status = cls._empty_activity_status(activity_type)
        try:
            status["activity_rows"] = cls._course_activity_rows(client, course_id, activity_type)
            if not status["activity_rows"]:
                status["available"] = False
                status["error"] = cls._no_activity_label(activity_type)
                return status
            for activity in status["activity_rows"]:
                submission_rows = (
                    client.list_assignment_submissions(course_id, activity["id"])
                    if activity_type == "assignment"
                    else client.list_quiz_submissions(course_id, activity["id"])
                )
                submitted_by_user_id = cls._activity_submissions_by_user_id(submission_rows, activity_type)
                for submitted_user_id, was_submitted in submitted_by_user_id.items():
                    if was_submitted:
                        status["submitted_activity_ids_by_user_id"][submitted_user_id].add(int(activity["id"]))
            status["activity_count"] = len(status["activity_rows"])
        except Exception as exc:  # noqa: BLE001
            status["available"] = False
            status["error"] = str(exc)
            status["activity_rows"] = []
            status["activity_count"] = 0
        return status

    @staticmethod
    def _missing_activity_rows_for_user(status: dict, user_id: int) -> list[dict]:
        if not status.get("available"):
            return []
        submitted_activity_ids = status.get("submitted_activity_ids_by_user_id", {}).get(int(user_id), set())
        return [
            activity
            for activity in status.get("activity_rows") or []
            if int(activity["id"]) not in submitted_activity_ids
        ]

    @staticmethod
    def _combined_activity_type(activity_reasons: list[str]) -> str:
        has_assignment = EngagementService.CRITERIA_MISSING_ASSIGNMENT in activity_reasons
        has_quiz = EngagementService.CRITERIA_MISSING_QUIZ in activity_reasons
        if has_assignment and has_quiz:
            return "mixed"
        return "quiz" if has_quiz else "assignment"

    @staticmethod
    def _activity_type_label(activity_type: str) -> str:
        labels = {
            "assignment": "Atividade integradora",
            "quiz": "Atividade objetiva",
            "mixed": "Atividade objetiva e atividade integradora",
        }
        return labels.get(activity_type, activity_type or "")

    @staticmethod
    def _missing_activities_label(assignment_rows: list[dict], quiz_rows: list[dict]) -> str:
        labels = []
        if quiz_rows:
            prefix = "Atividade objetiva" if len(quiz_rows) == 1 else "Atividades objetivas"
            labels.append(prefix + ": " + ", ".join(activity["name"] for activity in quiz_rows))
        if assignment_rows:
            prefix = "Atividade integradora" if len(assignment_rows) == 1 else "Atividades integradoras"
            labels.append(prefix + ": " + ", ".join(activity["name"] for activity in assignment_rows))
        return " | ".join(labels)

    @staticmethod
    def _combined_activity_error(assignment_status: dict, quiz_status: dict) -> str | None:
        errors = [
            status.get("error")
            for status in (assignment_status, quiz_status)
            if status.get("error")
        ]
        return " | ".join(errors) if errors else None

    @staticmethod
    def _course_activity_kind(needs_assignments: bool, needs_quizzes: bool) -> str:
        if needs_assignments and needs_quizzes:
            return "mixed"
        if needs_quizzes:
            return "quiz"
        if needs_assignments:
            return "assignment"
        return ""

    @staticmethod
    def _student_item_base(course_ref: str, course: dict, student: dict) -> dict:
        return {
            "course_ref": course_ref,
            "course_id": course.get("id"),
            "course_name": course.get("name"),
            "user_id": int(student.get("id")),
            "student_name": EngagementService._student_name(student),
        }

    @staticmethod
    def _analytics_by_user_id(rows: list[dict]) -> dict[int, dict]:
        result = {}
        for row in rows or []:
            user_id = row.get("id") or row.get("user_id")
            if user_id is None:
                continue
            try:
                result[int(user_id)] = row
            except (TypeError, ValueError):
                continue
        return result

    @staticmethod
    def _enrollments_by_user_id(rows: list[dict]) -> dict[int, dict]:
        result = {}
        for row in rows or []:
            user_id = row.get("user_id") or row.get("user", {}).get("id")
            if user_id is None:
                continue
            try:
                result[int(user_id)] = row
            except (TypeError, ValueError):
                continue
        return result

    @staticmethod
    def _has_never_accessed(row: dict) -> bool:
        if not row:
            return False
        return int(row.get("page_views") or 0) <= 0 and int(row.get("participations") or 0) <= 0

    @staticmethod
    def _has_low_total_activity(row: dict, max_minutes: float) -> bool:
        if not row:
            return False
        try:
            total_seconds = float(row.get("total_activity_time") or 0)
        except (TypeError, ValueError):
            total_seconds = 0
        return total_seconds < (float(max_minutes) * 60)

    @classmethod
    def _course_activity_rows(cls, client, course_id: str, activity_type: str) -> list[dict]:
        raw_items = client.list_course_quizzes(course_id) if activity_type == "quiz" else client.list_course_assignments(course_id)
        rows = []
        for item in raw_items:
            if item.get("id") is None:
                continue
            if activity_type == "assignment" and not cls._assignment_is_eligible_activity(item):
                continue
            if activity_type == "quiz" and not cls._quiz_is_eligible_activity(item):
                continue
            rows.append(
                {
                    "id": int(item["id"]),
                    "name": item.get("name") or item.get("title") or f"{'Quiz' if activity_type == 'quiz' else 'Assign'} {item['id']}",
                }
            )
        return rows

    @staticmethod
    def _assignment_is_quiz(assignment: dict) -> bool:
        submission_types = [str(item).lower() for item in assignment.get("submission_types") or []]
        return bool(assignment.get("quiz_id")) or "online_quiz" in submission_types

    @classmethod
    def _assignment_is_eligible_activity(cls, assignment: dict) -> bool:
        if assignment.get("published") is False:
            return False
        if cls._assignment_is_quiz(assignment):
            return False

        grading_type = str(assignment.get("grading_type") or "").lower()
        if grading_type == "not_graded":
            return False

        points_possible = assignment.get("points_possible")
        if points_possible is not None:
            try:
                if float(points_possible) <= 0:
                    return False
            except (TypeError, ValueError):
                pass

        submission_types = {str(item).lower() for item in assignment.get("submission_types") or []}
        if not submission_types:
            return True
        return (
            bool(submission_types & cls.EVALUATED_ASSIGNMENT_SUBMISSION_TYPES)
            and not submission_types <= cls.NON_EVALUATED_ASSIGNMENT_SUBMISSION_TYPES
        )

    @classmethod
    def _quiz_is_eligible_activity(cls, quiz: dict) -> bool:
        if quiz.get("published") is False:
            return False

        quiz_type = str(quiz.get("quiz_type") or "").lower()
        if quiz_type in cls.NON_EVALUATED_QUIZ_TYPES:
            return False
        if quiz_type and quiz_type not in cls.GRADED_QUIZ_TYPES:
            return False

        points_possible = quiz.get("points_possible")
        if points_possible is not None:
            try:
                if float(points_possible) <= 0:
                    return False
            except (TypeError, ValueError):
                pass
        return True

    @classmethod
    def _activity_submissions_by_user_id(cls, submissions: list[dict], activity_type: str) -> dict[int, bool]:
        submitted_by_user_id: dict[int, bool] = {}
        for submission in submissions:
            user_id = cls._submission_user_id(submission)
            if user_id is None:
                continue
            was_submitted = (
                cls._assignment_submission_done(submission)
                if activity_type == "assignment"
                else cls._quiz_submission_done(submission)
            )
            submitted_by_user_id[int(user_id)] = submitted_by_user_id.get(int(user_id), False) or was_submitted
        return submitted_by_user_id

    @staticmethod
    def _submission_user_id(submission: dict) -> int | None:
        user_id = submission.get("user_id")
        if user_id is None and isinstance(submission.get("submission"), dict):
            user_id = submission["submission"].get("user_id")
        if user_id is None:
            return None
        try:
            return int(user_id)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _assignment_submission_done(submission: dict) -> bool:
        workflow_state = str(submission.get("workflow_state") or "").lower()
        if workflow_state in {"submitted", "graded", "pending_review"}:
            return True
        if submission.get("submitted_at"):
            return True
        if EngagementService._submission_has_turn_in_content(submission):
            return True
        if submission.get("score") is not None:
            return True
        grade = submission.get("grade")
        return grade is not None and str(grade).strip() != ""

    @staticmethod
    def _submission_has_turn_in_content(submission: dict) -> bool:
        attachments = submission.get("attachments")
        if isinstance(attachments, list) and len(attachments) > 0:
            return True
        for key in ("body", "url", "media_comment_id", "annotatable_attachment_id"):
            if submission.get(key):
                return True
        nested_submission = submission.get("submission")
        if isinstance(nested_submission, dict):
            return EngagementService._submission_has_turn_in_content(nested_submission)
        return False

    @classmethod
    def _quiz_submission_done(cls, submission: dict) -> bool:
        workflow_state = str(submission.get("workflow_state") or "").lower()
        if workflow_state in {"complete", "completed", "pending_review"}:
            return True
        if submission.get("finished_at") or submission.get("end_at"):
            return True
        if submission.get("score") is not None or submission.get("kept_score") is not None:
            return True
        nested_submission = submission.get("submission")
        return isinstance(nested_submission, dict) and cls._assignment_submission_done(nested_submission)

    @staticmethod
    def _urgency_score(
        *,
        has_never_accessed: bool,
        has_low_activity: bool,
        has_missing_activity: bool,
    ) -> int:
        score = 0
        if has_never_accessed:
            score += 5
        if has_low_activity:
            score += 3
        if has_missing_activity:
            score += 4
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
        missing_activity_matches: int,
        never_accessed_matches: int,
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
            + (never_accessed_matches * 4)
            + (low_activity_matches * 2)
            + (missing_activity_matches * 3)
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

    @staticmethod
    def _csv_row_from_item(
        item: dict,
        *,
        sent: bool,
        dry_run: bool,
        conversation_id: int | str | None,
        error: str,
    ) -> dict:
        return {
            "course_ref": item["course_ref"],
            "course_id": item["course_id"],
            "course_name": item["course_name"],
            "user_id": item["user_id"],
            "student_name": item["student_name"],
            "message_kind": item.get("message_kind"),
            "message_kind_label": item.get("message_kind_label"),
            "page_views": item["page_views"],
            "participations": item["participations"],
            "last_activity_at": item.get("last_activity_at"),
            "total_activity_time_seconds": item.get("total_activity_time_seconds"),
            "requirement_count": item["requirement_count"],
            "requirement_completed_count": item["requirement_completed_count"],
            "completed_at": item["completed_at"],
            "activity_type": item.get("activity_type"),
            "activity_id": item.get("activity_id"),
            "activity_submitted": item.get("activity_submitted"),
            "activity_count": item.get("activity_count", 0),
            "activity_submitted_count": item.get("activity_submitted_count", 0),
            "activity_missing_count": item.get("activity_missing_count", 0),
            "missing_activity_names": "; ".join(item.get("missing_activity_names") or []),
            "missing_assignment_names": "; ".join(item.get("missing_assignment_names") or []),
            "missing_quiz_names": "; ".join(item.get("missing_quiz_names") or []),
            "reasons": item["reasons_label"],
            "sent": sent,
            "dry_run": dry_run,
            "conversation_id": conversation_id,
            "error": error,
        }

    @staticmethod
    def _csv_row_from_analysis_student(student: dict) -> dict:
        return {
            "course_ref": "; ".join(student.get("course_refs") or []),
            "course_id": "",
            "course_name": "; ".join(student.get("course_names") or []),
            "user_id": student.get("user_id"),
            "student_name": student.get("student_name"),
            "message_kind": "; ".join(student.get("message_kind_labels") or []),
            "message_kind_label": "; ".join(student.get("message_kind_labels") or []),
            "page_views": "",
            "participations": "",
            "last_activity_at": "",
            "total_activity_time_seconds": "",
            "requirement_count": "",
            "requirement_completed_count": "",
            "completed_at": "",
            "activity_type": "",
            "activity_id": "",
            "activity_submitted": "",
            "activity_count": "",
            "activity_submitted_count": "",
            "activity_missing_count": len(student.get("missing_activity_names") or []),
            "missing_activity_names": "; ".join(student.get("missing_activity_names") or []),
            "missing_assignment_names": "; ".join(student.get("missing_assignment_names") or []),
            "missing_quiz_names": "; ".join(student.get("missing_quiz_names") or []),
            "reasons": "; ".join(
                label
                for label, enabled in (
                    ("nunca entrou", student.get("never_accessed")),
                    ("menos de tempo", student.get("low_activity")),
                    ("nao realizou atividade objetiva", student.get("missing_quiz")),
                    ("nao realizou atividade integradora", student.get("missing_assignment")),
                )
                if enabled
            ),
            "sent": False,
            "dry_run": True,
            "conversation_id": "",
            "error": "",
            "analyzed_course_count": student.get("course_count", 0),
            "analyzed_courses": " | ".join(student.get("course_names") or []),
            "targeted": student.get("targeted", False),
            "clear": student.get("clear", False),
            "never_accessed": student.get("never_accessed", False),
            "low_activity": student.get("low_activity", False),
            "missing_quiz": student.get("missing_quiz", False),
            "missing_assignment": student.get("missing_assignment", False),
        }

    @staticmethod
    def _preview_course_result_row(course: dict, criteria: str) -> dict:
        target_messages = int(course.get("target_messages") or 0)
        return {
            "course_ref": course["course_ref"],
            "course_id": course["course_id"],
            "course_name": course["course_name"],
            "strategy_requested": criteria,
            "strategy_used": "preview_only",
            "students_found": course["students_found"],
            "manual_matches": course["matched_students"],
            "duplicates_skipped": 0,
            "recipients_targeted": target_messages,
            "inactivity_messages": course.get("inactivity_messages", 0),
            "activity_messages": course.get("activity_messages", 0),
            "recipients_sent": 0,
            "batch_count": 0,
            "status": "success" if target_messages else "skipped",
            "conversation_ids": [],
            "error": course.get("activity_filter_error"),
            "dry_run": True,
            "messageable_context": True,
            "manual_recipients": True,
            "analytics_available": course.get("analytics_available"),
            "progress_available": course.get("progress_available"),
            "enrollment_activity_available": course.get("enrollment_activity_available"),
            "never_accessed_matches": course.get("never_accessed_matches", 0),
            "incomplete_resources_matches": course.get("incomplete_resources_matches", 0),
            "inactive_days_matches": course.get("inactive_days_matches", 0),
            "low_activity_matches": course.get("low_activity_matches", 0),
            "missing_activity_matches": course.get("missing_activity_matches", 0),
            "missing_assignment_matches": course.get("missing_assignment_matches", 0),
            "missing_quiz_matches": course.get("missing_quiz_matches", 0),
            "activity_count": course.get("activity_count", 0),
            "activity_kind": course.get("activity_kind"),
            "activity_filter_available": course.get("activity_filter_available"),
            "activity_filter_error": course.get("activity_filter_error"),
            "matched_students_preview": [],
        }

    def _write_report(self, job_id: str, rows: list[dict], *, prefix: str = "engagement-report") -> str:
        report_filename = f"{prefix}-{job_id}.csv"
        report_path = Path(self.app_config.reports_dir) / report_filename
        fieldnames = [
            "course_ref",
            "course_id",
            "course_name",
            "user_id",
            "student_name",
            "message_kind",
            "message_kind_label",
            "page_views",
            "participations",
            "last_activity_at",
            "total_activity_time_seconds",
            "requirement_count",
            "requirement_completed_count",
            "completed_at",
            "activity_type",
            "activity_id",
            "activity_submitted",
            "activity_count",
            "activity_submitted_count",
            "activity_missing_count",
            "missing_activity_names",
            "missing_assignment_names",
            "missing_quiz_names",
            "reasons",
            "sent",
            "dry_run",
            "conversation_id",
            "error",
            "analyzed_course_count",
            "analyzed_courses",
            "targeted",
            "clear",
            "never_accessed",
            "low_activity",
            "missing_quiz",
            "missing_assignment",
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
