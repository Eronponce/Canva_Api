from __future__ import annotations

import csv
from pathlib import Path

from src.services.canvas_client import CanvasApiError
from src.utils.parsing import chunked, parse_course_references
from src.utils.time_utils import utc_now_iso


class MessageService:
    MAX_RECIPIENTS_PER_CALL = 100

    def __init__(self, app_config, connection_service, job_manager):
        self.app_config = app_config
        self.connection_service = connection_service
        self.job_manager = job_manager

    def run_job(self, job_id: str, payload: dict) -> None:
        course_refs = parse_course_references(payload.get("course_ids_text", ""))
        subject = (payload.get("subject") or "").strip()
        message = (payload.get("message") or "").strip()
        requested_strategy = payload.get("strategy") or "users"
        dedupe = bool(payload.get("dedupe"))
        dry_run = bool(payload.get("dry_run"))

        if not course_refs:
            raise ValueError("Informe pelo menos uma turma para enviar as mensagens.")
        if not subject:
            raise ValueError("Informe o assunto da mensagem.")
        if not message:
            raise ValueError("Informe o corpo da mensagem.")

        client = self.connection_service.build_client(payload)
        user = client.get_current_user()

        effective_strategy = requested_strategy
        if requested_strategy == "context" and dedupe:
            effective_strategy = "users"
            self.job_manager.add_log(
                job_id,
                level="warning",
                message="Deduplicação exige envio por usuário. A estratégia foi ajustada automaticamente.",
            )

        total_steps = max(len(course_refs) * 2, 1)
        self.job_manager.mark_running(
            job_id,
            total=total_steps,
            step="Validando acesso ao Canvas",
        )
        self.job_manager.add_log(
            job_id,
            level="info",
            message="Conexão validada para o envio de mensagens.",
            data={"user_id": user.get("id"), "user_name": user.get("name")},
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
            students = [
                student
                for student in client.list_course_students(str(course.get("id")))
                if not student.get("is_test_student")
            ]

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
                    message="Não foi possível validar o contexto da turma via Search Recipients.",
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

            student_ids = [student["id"] for student in prepared_course["students"]]
            total_students_found += len(student_ids)

            result_row = {
                "course_ref": prepared_course["course_ref"],
                "course_id": prepared_course["course_id"],
                "course_name": prepared_course["course_name"],
                "strategy_requested": requested_strategy,
                "strategy_used": effective_strategy,
                "students_found": len(student_ids),
                "duplicates_skipped": 0,
                "recipients_targeted": 0,
                "recipients_sent": 0,
                "batch_count": 0,
                "status": "success",
                "conversation_ids": [],
                "error": None,
                "dry_run": dry_run,
                "messageable_context": bool(prepared_course["context_match"]),
            }

            if effective_strategy == "users":
                target_ids = []
                for student_id in student_ids:
                    if dedupe and student_id in seen_user_ids:
                        result_row["duplicates_skipped"] += 1
                        total_duplicates_skipped += 1
                        continue
                    if dedupe:
                        seen_user_ids.add(student_id)
                    target_ids.append(student_id)

                result_row["strategy_used"] = "users"
            else:
                target_ids = student_ids
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
                    message="Nenhum destinatário elegível para a turma.",
                    data={"course_id": prepared_course["course_id"]},
                )
                self.job_manager.set_progress(
                    job_id,
                    current=step_index,
                    total=total_steps,
                    step=f"Turma {prepared_course['course_name']} concluída",
                )
                continue

            if dry_run:
                self.job_manager.add_log(
                    job_id,
                    level="info",
                    message="Dry run da caixa de entrada concluído para a turma.",
                    data={
                        "course_id": prepared_course["course_id"],
                        "strategy_used": result_row["strategy_used"],
                        "recipients_targeted": len(target_ids),
                    },
                )
                self.job_manager.set_progress(
                    job_id,
                    current=step_index,
                    total=total_steps,
                    step=f"Turma {prepared_course['course_name']} concluída",
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
                        )
                        result_row["conversation_ids"].extend(self._extract_conversation_ids(response))
                        result_row["recipients_sent"] += len(recipient_chunk)
                        total_recipients_sent += len(recipient_chunk)
                    except CanvasApiError as exc:
                        batch_failures.append(exc.message)
                        self.job_manager.add_log(
                            job_id,
                            level="error",
                            message="Falha em lote de envio por usuário.",
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
                            message="Erro inesperado em lote de envio por usuário.",
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
                    message="Envio por usuário concluído para a turma.",
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
                step=f"Turma {prepared_course['course_name']} concluída",
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

    def _extract_conversation_ids(self, response) -> list[int]:
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
            "duplicates_skipped",
            "recipients_targeted",
            "recipients_sent",
            "batch_count",
            "status",
            "conversation_ids",
            "dry_run",
            "messageable_context",
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
