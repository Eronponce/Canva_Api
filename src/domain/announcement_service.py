from __future__ import annotations

import csv
from pathlib import Path

from src.services.canvas_client import CanvasApiError
from src.utils.parsing import parse_course_references
from src.utils.time_utils import parse_schedule_datetime, utc_now_iso


class AnnouncementService:
    def __init__(self, app_config, connection_service, job_manager):
        self.app_config = app_config
        self.connection_service = connection_service
        self.job_manager = job_manager

    def run_job(self, job_id: str, payload: dict) -> None:
        course_refs = parse_course_references(payload.get("course_ids_text", ""))
        title = (payload.get("title") or "").strip()
        message_html = (payload.get("message_html") or "").strip()
        publish_mode = payload.get("publish_mode") or "publish_now"
        lock_comment = bool(payload.get("lock_comment"))
        dry_run = bool(payload.get("dry_run"))
        client_timezone = payload.get("client_timezone")

        if not course_refs:
            raise ValueError("Informe pelo menos uma turma para publicar o comunicado.")
        if not title:
            raise ValueError("Informe o título do comunicado.")
        if not message_html:
            raise ValueError("Informe a mensagem HTML do comunicado.")

        delayed_post_at = None
        published = True

        if publish_mode == "draft":
            published = False
        elif publish_mode == "schedule":
            delayed_post_at = parse_schedule_datetime(payload.get("schedule_at_local", ""), client_timezone)
            if not delayed_post_at:
                raise ValueError("Informe a data e hora do agendamento.")
            published = True

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
            dry_run=dry_run,
            canvas_user_id=user.get("id"),
            canvas_user_name=user.get("name") or user.get("short_name") or "",
        )

        self.job_manager.mark_running(
            job_id,
            total=len(course_refs),
            step="Validando acesso ao Canvas",
        )
        self.job_manager.add_log(
            job_id,
            level="info",
            message="Conexão validada com sucesso.",
            data={"user_id": user.get("id"), "user_name": user.get("name")},
        )

        course_results = []
        for index, course_ref in enumerate(course_refs, start=1):
            self.job_manager.set_progress(
                job_id,
                current=index - 1,
                total=len(course_refs),
                step=f"Processando turma {course_ref}",
            )
            self.job_manager.add_log(
                job_id,
                level="info",
                message="Iniciando processamento da turma.",
                data={"course_ref": course_ref},
            )

            try:
                course = client.get_course(course_ref)
                result_row = {
                    "course_ref": course_ref,
                    "course_id": course.get("id"),
                    "course_name": course.get("name"),
                    "status": "success",
                    "announcement_id": None,
                    "announcement_url": None,
                    "published": published,
                    "delayed_post_at": delayed_post_at,
                    "dry_run": dry_run,
                    "error": None,
                }

                if dry_run:
                    self.job_manager.add_log(
                        job_id,
                        level="info",
                        message="Dry run do comunicado concluído para a turma.",
                        data={"course_id": course.get("id"), "course_name": course.get("name")},
                    )
                else:
                    response = client.create_announcement(
                        course_ref=str(course.get("id")),
                        title=title,
                        message_html=message_html,
                        published=published,
                        delayed_post_at=delayed_post_at,
                        lock_comment=lock_comment,
                    )
                    result_row["announcement_id"] = response.get("id")
                    result_row["announcement_url"] = response.get("html_url")
                    result_row["published"] = response.get("published", published)
                    self.job_manager.add_log(
                        job_id,
                        level="info",
                        message="Comunicado criado com sucesso.",
                        data={
                            "course_id": course.get("id"),
                            "announcement_id": response.get("id"),
                        },
                    )

                course_results.append(result_row)
            except CanvasApiError as exc:
                self.job_manager.add_log(
                    job_id,
                    level="error",
                    message="Falha ao publicar comunicado na turma.",
                    data={"course_ref": course_ref, "error": exc.to_dict()},
                )
                course_results.append(
                    {
                        "course_ref": course_ref,
                        "course_id": None,
                        "course_name": None,
                        "status": "error",
                        "announcement_id": None,
                        "announcement_url": None,
                        "published": published,
                        "delayed_post_at": delayed_post_at,
                        "dry_run": dry_run,
                        "error": exc.message,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                self.job_manager.add_log(
                    job_id,
                    level="error",
                    message="Erro inesperado ao processar a turma.",
                    data={"course_ref": course_ref, "error": str(exc)},
                )
                course_results.append(
                    {
                        "course_ref": course_ref,
                        "course_id": None,
                        "course_name": None,
                        "status": "error",
                        "announcement_id": None,
                        "announcement_url": None,
                        "published": published,
                        "delayed_post_at": delayed_post_at,
                        "dry_run": dry_run,
                        "error": str(exc),
                    }
                )
            finally:
                self.job_manager.set_progress(
                    job_id,
                    current=index,
                    total=len(course_refs),
                    step=f"Turma {course_ref} concluída",
                )

        summary = {
            "requested_at": utc_now_iso(),
            "requested_by": {
                "id": user.get("id"),
                "name": user.get("name"),
            },
            "courses_processed": len(course_results),
            "success_count": len([row for row in course_results if row["status"] == "success"]),
            "failure_count": len([row for row in course_results if row["status"] == "error"]),
            "dry_run": dry_run,
            "publish_mode": publish_mode,
            "lock_comment": lock_comment,
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

    def _write_report(self, job_id: str, rows: list[dict]) -> str:
        report_filename = f"announcement-report-{job_id}.csv"
        report_path = Path(self.app_config.reports_dir) / report_filename
        fieldnames = [
            "course_ref",
            "course_id",
            "course_name",
            "status",
            "announcement_id",
            "announcement_url",
            "published",
            "delayed_post_at",
            "dry_run",
            "error",
        ]

        with report_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return report_filename
