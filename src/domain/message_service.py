from __future__ import annotations

import csv
from pathlib import Path

from src.services.canvas_client import CanvasApiError
from src.utils.attachment_utils import delete_temp_file
from src.utils.parsing import chunked, parse_course_references
from src.utils.time_utils import utc_now_iso


class MessageService:
    MAX_RECIPIENTS_PER_CALL = 100

    def __init__(self, app_config, connection_service, job_manager):
        self.app_config = app_config
        self.connection_service = connection_service
        self.job_manager = job_manager

    def preview_recipients(self, payload: dict) -> dict:
        course_refs = parse_course_references(payload.get("course_ids_text", ""))
        if not course_refs:
            raise ValueError("Selecione ao menos uma turma para listar os destinatarios.")

        client = self.connection_service.build_client(payload)
        recipients_by_id: dict[str, dict] = {}
        courses = []
        total_students_found = 0

        for course_ref in course_refs:
            course = client.get_course(course_ref)
            students = self._course_students(client, course)
            total_students_found += len(students)
            courses.append(
                {
                    "course_ref": course_ref,
                    "course_id": course.get("id"),
                    "course_name": course.get("name"),
                    "students_found": len(students),
                }
            )

            for student in students:
                user_id = student.get("id")
                if user_id is None:
                    continue

                recipient = recipients_by_id.setdefault(
                    str(user_id),
                    {
                        "user_id": user_id,
                        "name": self._student_name(student),
                        "short_name": student.get("short_name") or "",
                        "sortable_name": student.get("sortable_name") or "",
                        "login_id": student.get("login_id") or "",
                        "sis_user_id": student.get("sis_user_id") or "",
                        "course_refs": [],
                        "course_names": [],
                    },
                )
                if course_ref not in recipient["course_refs"]:
                    recipient["course_refs"].append(course_ref)
                course_name = course.get("name") or str(course_ref)
                if course_name not in recipient["course_names"]:
                    recipient["course_names"].append(course_name)

        items = sorted(
            recipients_by_id.values(),
            key=lambda item: ((item.get("name") or "").lower(), item.get("user_id") or 0),
        )
        return {
            "items": items,
            "courses": courses,
            "total_students_found": total_students_found,
            "unique_recipients": len(items),
        }

    def run_job(self, job_id: str, payload: dict) -> None:
        course_refs = parse_course_references(payload.get("course_ids_text", ""))
        subject = (payload.get("subject") or "").strip()
        message = (payload.get("message") or "").strip()
        requested_strategy = payload.get("strategy") or "users"
        dedupe = bool(payload.get("dedupe"))
        dry_run = bool(payload.get("dry_run"))
        manual_recipients = bool(payload.get("manual_recipients"))
        selected_user_ids = self._selected_user_ids(payload)
        attachment = self._attachment_payload(payload)

        if not course_refs:
            raise ValueError("Informe pelo menos uma turma para enviar as mensagens.")
        if not subject:
            raise ValueError("Informe o assunto da mensagem.")
        if not message:
            raise ValueError("Informe o corpo da mensagem.")
        if manual_recipients and not selected_user_ids:
            raise ValueError("Selecione pelo menos um destinatario manual para a caixa de entrada.")

        effective_strategy = requested_strategy
        client = self.connection_service.build_client(payload)
        user = client.get_current_user()
        self.job_manager.update_metadata(
            job_id,
            base_url=payload.get("base_url") or "",
            request_payload=self._metadata_payload(payload, attachment),
            request_token_source="inline" if (payload.get("access_token") or payload.get("api_token")) else self.connection_service.app_config.default_token_source,
            requested_strategy=requested_strategy,
            effective_strategy=effective_strategy,
            dry_run=dry_run,
            dedupe=dedupe,
            canvas_user_id=user.get("id"),
            canvas_user_name=user.get("name") or user.get("short_name") or "",
        )

        if requested_strategy == "context" and (dedupe or manual_recipients):
            effective_strategy = "users"
            self.job_manager.add_log(
                job_id,
                level="warning",
                message="A estrategia foi ajustada automaticamente para envio por usuario.",
                data={
                    "dedupe": dedupe,
                    "manual_recipients": manual_recipients,
                },
            )
            self.job_manager.update_metadata(job_id, effective_strategy=effective_strategy)

        uploaded_attachment = None
        if attachment:
            try:
                if not dry_run:
                    uploaded_attachment = client.upload_conversation_attachment(
                        file_path=attachment["temp_path"],
                        filename=attachment["original_name"],
                        content_type=attachment["content_type"],
                        size=attachment["size"],
                    )
                    self.job_manager.add_log(
                        job_id,
                        level="info",
                        message="Anexo enviado para o Canvas e pronto para reutilizacao no lote.",
                        data={
                            "attachment_name": attachment["original_name"],
                            "canvas_file_id": uploaded_attachment.get("id"),
                        },
                    )
            except CanvasApiError as exc:
                self.job_manager.add_log(
                    job_id,
                    level="error",
                    message="Falha ao preparar o anexo da caixa de entrada.",
                    data={"error": exc.to_dict()},
                )
                raise ValueError("Nao foi possivel preparar o anexo para a caixa de entrada.") from exc
            finally:
                delete_temp_file(attachment.get("temp_path"))
                attachment["temp_path"] = ""

        attachment_ids = [int(uploaded_attachment["id"])] if uploaded_attachment and uploaded_attachment.get("id") is not None else []

        total_steps = max(len(course_refs) * 2, 1)
        self.job_manager.mark_running(
            job_id,
            total=total_steps,
            step="Validando acesso ao Canvas",
        )
        self.job_manager.add_log(
            job_id,
            level="info",
            message="Conexao validada para o envio de mensagens.",
            data={"user_id": user.get("id"), "user_name": user.get("name")},
        )
        if attachment:
            self.job_manager.add_log(
                job_id,
                level="info",
                message="Lote da caixa de entrada contem anexo.",
                data={
                    "attachment_name": attachment["original_name"],
                    "attachment_size": attachment["size"],
                    "dry_run": dry_run,
                },
            )

        prepared_courses = []
        step_index = 0
        for course_ref in course_refs:
            step_index += 1
            self.job_manager.set_progress(
                job_id,
                current=step_index - 1,
                total=total_steps,
                step=f"Carregando turma {course_ref}",
            )

            course = client.get_course(course_ref)
            students = self._course_students(client, course)

            context_match = None
            try:
                context_match = client.find_messageable_context(
                    course_id=course.get("id"),
                    course_name=course.get("name") or str(course.get("id")),
                )
            except Exception as exc:  # noqa: BLE001
                self.job_manager.add_log(
                    job_id,
                    level="warning",
                    message="Nao foi possivel validar o contexto da turma via Search Recipients.",
                    data={"course_id": course.get("id"), "error": str(exc)},
                )

            prepared_courses.append(
                {
                    "course_ref": course_ref,
                    "course_id": course.get("id"),
                    "course_name": course.get("name"),
                    "context_code": f"course_{course.get('id')}",
                    "students": students,
                    "context_match": context_match,
                }
            )
            self.job_manager.add_log(
                job_id,
                level="info",
                message="Turma carregada para envio.",
                data={
                    "course_id": course.get("id"),
                    "course_name": course.get("name"),
                    "students_found": len(students),
                    "messageable_context": bool(context_match),
                },
            )
            self.job_manager.set_progress(
                job_id,
                current=step_index,
                total=total_steps,
                step=f"Turma {course_ref} carregada",
            )

        course_results = []
        seen_user_ids: set[int] = set()
        total_students_found = 0
        total_recipients_targeted = 0
        total_recipients_sent = 0
        total_duplicates_skipped = 0

        for prepared_course in prepared_courses:
            step_index += 1
            self.job_manager.set_progress(
                job_id,
                current=step_index - 1,
                total=total_steps,
                step=f"Enviando na turma {prepared_course['course_name']}",
            )

            student_ids = [
                int(student["id"])
                for student in prepared_course["students"]
                if student.get("id") is not None
            ]
            total_students_found += len(student_ids)
            eligible_student_ids = [
                student_id
                for student_id in student_ids
                if not manual_recipients or student_id in selected_user_ids
            ]

            result_row = {
                "course_ref": prepared_course["course_ref"],
                "course_id": prepared_course["course_id"],
                "course_name": prepared_course["course_name"],
                "strategy_requested": requested_strategy,
                "strategy_used": effective_strategy,
                "students_found": len(student_ids),
                "manual_matches": len(eligible_student_ids),
                "duplicates_skipped": 0,
                "recipients_targeted": 0,
                "recipients_sent": 0,
                "batch_count": 0,
                "status": "success",
                "conversation_ids": [],
                "attachment_name": attachment["original_name"] if attachment else "",
                "attachment_file_id": attachment_ids[0] if attachment_ids else None,
                "error": None,
                "dry_run": dry_run,
                "messageable_context": bool(prepared_course["context_match"]),
                "manual_recipients": manual_recipients,
            }

            if effective_strategy == "users":
                target_ids = []
                for student_id in eligible_student_ids:
                    if dedupe and student_id in seen_user_ids:
                        result_row["duplicates_skipped"] += 1
                        total_duplicates_skipped += 1
                        continue
                    if dedupe:
                        seen_user_ids.add(student_id)
                    target_ids.append(student_id)

                result_row["strategy_used"] = "users"
            else:
                target_ids = eligible_student_ids
                if len(target_ids) > self.MAX_RECIPIENTS_PER_CALL:
                    result_row["strategy_used"] = "users_fallback"

            result_row["recipients_targeted"] = len(target_ids)
            total_recipients_targeted += len(target_ids)

            if not target_ids:
                result_row["status"] = "skipped"
                course_results.append(result_row)
                self.job_manager.add_log(
                    job_id,
                    level="info",
                    message="Nenhum destinatario elegivel para a turma.",
                    data={"course_id": prepared_course["course_id"]},
                )
                self.job_manager.set_progress(
                    job_id,
                    current=step_index,
                    total=total_steps,
                    step=f"Turma {prepared_course['course_name']} concluida",
                )
                continue

            if dry_run:
                self.job_manager.add_log(
                    job_id,
                    level="info",
                    message="Dry run da caixa de entrada concluido para a turma.",
                    data={
                        "course_id": prepared_course["course_id"],
                        "strategy_used": result_row["strategy_used"],
                        "recipients_targeted": len(target_ids),
                        "manual_matches": result_row["manual_matches"],
                    },
                )
                self.job_manager.set_progress(
                    job_id,
                    current=step_index,
                    total=total_steps,
                    step=f"Turma {prepared_course['course_name']} concluida",
                )
                course_results.append(result_row)
                continue

            if result_row["strategy_used"] == "context":
                try:
                    response = client.create_conversation(
                        recipients=[prepared_course["context_code"]],
                        subject=subject,
                        body=message,
                        context_code=prepared_course["context_code"],
                        force_new=True,
                        group_conversation=False,
                        attachment_ids=attachment_ids,
                    )
                    result_row["conversation_ids"] = self._extract_conversation_ids(response)
                    result_row["recipients_sent"] = len(target_ids)
                    total_recipients_sent += len(target_ids)
                    self.job_manager.add_log(
                        job_id,
                        level="info",
                        message="Mensagem enviada por contexto da turma.",
                        data={
                            "course_id": prepared_course["course_id"],
                            "recipients_sent": len(target_ids),
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    result_row["status"] = "error"
                    result_row["error"] = str(exc)
                    self.job_manager.add_log(
                        job_id,
                        level="error",
                        message="Falha ao enviar mensagem por contexto.",
                        data={"course_id": prepared_course["course_id"], "error": str(exc)},
                    )
            else:
                batch_failures = []
                for recipient_chunk in chunked(target_ids, self.MAX_RECIPIENTS_PER_CALL):
                    result_row["batch_count"] += 1
                    try:
                        response = client.create_conversation(
                            recipients=recipient_chunk,
                            subject=subject,
                            body=message,
                            context_code=prepared_course["context_code"],
                            force_new=True,
                            group_conversation=False,
                            attachment_ids=attachment_ids,
                        )
                        result_row["conversation_ids"].extend(self._extract_conversation_ids(response))
                        result_row["recipients_sent"] += len(recipient_chunk)
                        total_recipients_sent += len(recipient_chunk)
                    except CanvasApiError as exc:
                        batch_failures.append(exc.message)
                        self.job_manager.add_log(
                            job_id,
                            level="error",
                            message="Falha em lote de envio por usuario.",
                            data={
                                "course_id": prepared_course["course_id"],
                                "batch_size": len(recipient_chunk),
                                "error": exc.to_dict(),
                            },
                        )
                    except Exception as exc:  # noqa: BLE001
                        batch_failures.append(str(exc))
                        self.job_manager.add_log(
                            job_id,
                            level="error",
                            message="Erro inesperado em lote de envio por usuario.",
                            data={
                                "course_id": prepared_course["course_id"],
                                "batch_size": len(recipient_chunk),
                                "error": str(exc),
                            },
                        )

                if batch_failures and result_row["recipients_sent"] == 0:
                    result_row["status"] = "error"
                elif batch_failures:
                    result_row["status"] = "partial"

                if batch_failures:
                    result_row["error"] = " | ".join(batch_failures)

                self.job_manager.add_log(
                    job_id,
                    level="info",
                    message="Envio por usuario concluido para a turma.",
                    data={
                        "course_id": prepared_course["course_id"],
                        "recipients_sent": result_row["recipients_sent"],
                        "batch_count": result_row["batch_count"],
                        "status": result_row["status"],
                    },
                )

            course_results.append(result_row)
            self.job_manager.set_progress(
                job_id,
                current=step_index,
                total=total_steps,
                step=f"Turma {prepared_course['course_name']} concluida",
            )

        summary = {
            "requested_at": utc_now_iso(),
            "requested_by": {
                "id": user.get("id"),
                "name": user.get("name"),
            },
            "requested_strategy": requested_strategy,
            "effective_strategy": effective_strategy,
            "dry_run": dry_run,
            "dedupe": dedupe,
            "manual_recipients": manual_recipients,
            "selected_user_count": len(selected_user_ids),
            "has_attachment": bool(attachment),
            "attachment_name": attachment["original_name"] if attachment else "",
            "attachment_file_id": attachment_ids[0] if attachment_ids else None,
            "total_courses": len(course_results),
            "total_students_found": total_students_found,
            "total_recipients_targeted": total_recipients_targeted,
            "total_recipients_sent": total_recipients_sent,
            "total_duplicates_skipped": total_duplicates_skipped,
            "success_count": len([row for row in course_results if row["status"] == "success"]),
            "partial_count": len([row for row in course_results if row["status"] == "partial"]),
            "failure_count": len([row for row in course_results if row["status"] == "error"]),
            "skipped_count": len([row for row in course_results if row["status"] == "skipped"]),
        }

        report_filename = self._write_report(job_id, course_results)
        self.job_manager.complete(
            job_id,
            result={
                "summary": summary,
                "course_results": course_results,
            },
            report_filename=report_filename,
        )

    @staticmethod
    def _extract_conversation_ids(response) -> list[int]:
        if isinstance(response, list):
            return [item.get("id") for item in response if item.get("id") is not None]
        if isinstance(response, dict) and response.get("id") is not None:
            return [response["id"]]
        return []

    def _write_report(self, job_id: str, rows: list[dict]) -> str:
        report_filename = f"message-report-{job_id}.csv"
        report_path = Path(self.app_config.reports_dir) / report_filename
        fieldnames = [
            "course_ref",
            "course_id",
            "course_name",
            "strategy_requested",
            "strategy_used",
            "students_found",
            "manual_matches",
            "duplicates_skipped",
            "recipients_targeted",
            "recipients_sent",
            "batch_count",
            "status",
            "conversation_ids",
            "attachment_name",
            "attachment_file_id",
            "dry_run",
            "messageable_context",
            "manual_recipients",
            "error",
        ]

        with report_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                serializable = dict(row)
                serializable["conversation_ids"] = ",".join(
                    str(value) for value in row.get("conversation_ids", [])
                )
                writer.writerow(serializable)

        return report_filename

    @staticmethod
    def _selected_user_ids(payload: dict) -> set[int]:
        values = payload.get("selected_user_ids") or []
        if not isinstance(values, list):
            return set()

        selected: set[int] = set()
        for value in values:
            try:
                selected.add(int(value))
            except (TypeError, ValueError):
                continue
        return selected

    @staticmethod
    def _attachment_payload(payload: dict) -> dict | None:
        temp_path = str(payload.get("attachment_temp_path") or "").strip()
        original_name = str(payload.get("attachment_name") or "").strip()
        if not temp_path or not original_name:
            return None
        return {
            "temp_path": temp_path,
            "original_name": original_name,
            "content_type": str(payload.get("attachment_content_type") or "application/octet-stream").strip() or "application/octet-stream",
            "size": int(payload.get("attachment_size") or 0),
        }

    @staticmethod
    def _metadata_payload(payload: dict, attachment: dict | None) -> dict:
        data = {
            key: value
            for key, value in payload.items()
            if key
            not in {
                "access_token",
                "api_token",
                "attachment_temp_path",
                "attachment_name",
                "attachment_content_type",
                "attachment_size",
            }
        }
        if attachment:
            data["attachment"] = {
                "name": attachment["original_name"],
                "content_type": attachment["content_type"],
                "size": attachment["size"],
            }
        return data

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
