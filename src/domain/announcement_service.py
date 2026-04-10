from __future__ import annotations

import csv
import re
from pathlib import Path

from src.services.canvas_client import CanvasApiError
from src.utils.attachment_utils import delete_temp_file
from src.utils.parsing import parse_course_references
from src.utils.time_utils import parse_schedule_datetime, utc_now_iso


class AnnouncementService:
    def __init__(self, app_config, connection_service, job_manager, job_repository):
        self.app_config = app_config
        self.connection_service = connection_service
        self.job_manager = job_manager
        self.job_repository = job_repository

    def run_job(self, job_id: str, payload: dict) -> None:
        course_refs = parse_course_references(payload.get("course_ids_text", ""))
        title = (payload.get("title") or "").strip()
        message_html = (payload.get("message_html") or "").strip()
        publish_mode = payload.get("publish_mode") or "publish_now"
        lock_comment = bool(payload.get("lock_comment"))
        dry_run = bool(payload.get("dry_run"))
        client_timezone = payload.get("client_timezone")
        attachment = self._attachment_payload(payload)

        if not course_refs:
            raise ValueError("Informe pelo menos uma turma para publicar o comunicado.")
        if not title:
            raise ValueError("Informe o titulo do comunicado.")
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

        try:
            client = self.connection_service.build_client(payload)
            user = client.get_current_user()
            self.job_manager.update_metadata(
                job_id,
                base_url=payload.get("base_url") or "",
                request_payload=self._metadata_payload(payload, attachment),
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
                message="Conexao validada com sucesso.",
                data={"user_id": user.get("id"), "user_name": user.get("name")},
            )
            if attachment:
                self.job_manager.add_log(
                    job_id,
                    level="info",
                    message="Anexo preparado para o lote de comunicados.",
                    data={
                        "attachment_name": attachment["original_name"],
                        "attachment_size": attachment["size"],
                        "attachment_content_type": attachment["content_type"],
                    },
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
                    rendered_title = self._render_template(
                        title,
                        course_name=course.get("name"),
                        course_ref=course_ref,
                        course_code=course.get("course_code"),
                    )
                    rendered_message_html = self._render_template(
                        message_html,
                        course_name=course.get("name"),
                        course_ref=course_ref,
                        course_code=course.get("course_code"),
                    )
                    result_row = {
                        "course_ref": course_ref,
                        "course_id": course.get("id"),
                        "course_name": course.get("name"),
                        "course_code": course.get("course_code"),
                        "status": "success",
                        "title": rendered_title,
                        "message_html": rendered_message_html,
                        "lock_comment": lock_comment,
                        "announcement_id": None,
                        "announcement_url": None,
                        "published": published,
                        "delayed_post_at": delayed_post_at,
                        "dry_run": dry_run,
                        "attachment_name": attachment["original_name"] if attachment else "",
                        "error": None,
                    }

                    if dry_run:
                        self.job_manager.add_log(
                            job_id,
                            level="info",
                            message="Dry run do comunicado concluido para a turma.",
                            data={"course_id": course.get("id"), "course_name": course.get("name")},
                        )
                    else:
                        response = client.create_announcement(
                            course_ref=str(course.get("id")),
                            title=rendered_title,
                            message_html=rendered_message_html,
                            published=published,
                            delayed_post_at=delayed_post_at,
                            lock_comment=lock_comment,
                            attachment=attachment,
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
                                "attachment_name": attachment["original_name"] if attachment else None,
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
                            "attachment_name": attachment["original_name"] if attachment else "",
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
                            "attachment_name": attachment["original_name"] if attachment else "",
                            "error": str(exc),
                        }
                    )
                finally:
                    self.job_manager.set_progress(
                        job_id,
                        current=index,
                        total=len(course_refs),
                        step=f"Turma {course_ref} concluida",
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
                "has_attachment": bool(attachment),
                "attachment_name": attachment["original_name"] if attachment else "",
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
        finally:
            delete_temp_file((attachment or {}).get("temp_path"))

    def preview_job(self, payload: dict) -> dict:
        course_refs = parse_course_references(payload.get("course_ids_text", ""))
        title = (payload.get("title") or "").strip()
        message_html = (payload.get("message_html") or "").strip()
        publish_mode = payload.get("publish_mode") or "publish_now"
        client_timezone = payload.get("client_timezone")
        attachment = self._attachment_payload(payload)

        if not course_refs:
            raise ValueError("Selecione ao menos uma turma para revisar o comunicado.")
        if not title:
            raise ValueError("Informe o titulo do comunicado.")
        if not message_html:
            raise ValueError("Informe a mensagem HTML do comunicado.")

        delayed_post_at = None
        if publish_mode == "schedule":
            delayed_post_at = parse_schedule_datetime(payload.get("schedule_at_local", ""), client_timezone)
            if not delayed_post_at:
                raise ValueError("Informe a data e hora do agendamento.")

        client = self.connection_service.build_client(payload)
        courses = []
        for course_ref in course_refs:
            try:
                course = client.get_course(course_ref)
                courses.append(
                    {
                        "course_ref": str(course_ref),
                        "course_id": course.get("id"),
                        "course_name": course.get("name") or str(course_ref),
                        "course_code": course.get("course_code") or "",
                        "status": "ok",
                    }
                )
            except Exception as exc:  # noqa: BLE001
                courses.append(
                    {
                        "course_ref": str(course_ref),
                        "course_id": None,
                        "course_name": "",
                        "course_code": "",
                        "status": "error",
                        "error": str(exc),
                    }
                )

        return {
            "summary": {
                "courses_requested": len(course_refs),
                "success_count": len([item for item in courses if item["status"] == "ok"]),
                "failure_count": len([item for item in courses if item["status"] == "error"]),
                "publish_mode": publish_mode,
                "delayed_post_at": delayed_post_at,
                "lock_comment": bool(payload.get("lock_comment")),
                "dry_run": bool(payload.get("dry_run")),
                "has_attachment": bool(attachment),
                "attachment_name": attachment["original_name"] if attachment else "",
            },
            "courses": courses,
        }

    def get_edit_target(self, job_id: str, *, course_ref: str, announcement_id: int | str) -> dict:
        target = self._editable_target(job_id, course_ref=course_ref, announcement_id=announcement_id)
        title, message_html, lock_comment = self._resolved_edit_content(target)
        return {
            "job_id": target["job_id"],
            "course_ref": target["course_ref"],
            "course_id": target["canvas_course_id"] or target["course_id"],
            "course_name": target["course_name"],
            "announcement_id": target["announcement_id"],
            "announcement_url": target["announcement_url"],
            "base_url": target["base_url"],
            "published": target["published"],
            "delayed_post_at": target["delayed_post_at"],
            "title": title,
            "message_html": message_html,
            "lock_comment": lock_comment,
        }

    def update_history_announcement(self, job_id: str, *, announcement_id: int | str, payload: dict) -> dict:
        course_ref = str(payload.get("course_ref") or "").strip()
        title = str(payload.get("title") or "").strip()
        message_html = str(payload.get("message_html") or "").strip()
        lock_comment = bool(payload.get("lock_comment"))

        if not course_ref:
            raise ValueError("Nao foi possivel identificar a turma do comunicado.")
        if not title:
            raise ValueError("Informe o titulo corrigido do comunicado.")
        if not message_html:
            raise ValueError("Informe a mensagem corrigida do comunicado.")

        target = self._editable_target(job_id, course_ref=course_ref, announcement_id=announcement_id)
        rendered_title = self._render_template(
            title,
            course_name=target["course_name"],
            course_ref=target["course_ref"],
            course_code=(target["raw_result"] or {}).get("course_code"),
        )
        rendered_message_html = self._render_template(
            message_html,
            course_name=target["course_name"],
            course_ref=target["course_ref"],
            course_code=(target["raw_result"] or {}).get("course_code"),
        )

        client_payload = dict(payload)
        if not str(client_payload.get("base_url") or "").strip() and target.get("base_url"):
            client_payload["base_url"] = target["base_url"]
        client = self.connection_service.build_client(client_payload)
        canvas_course_ref = str(target["canvas_course_id"] or target["course_ref"])
        response = client.update_announcement(
            course_ref=canvas_course_ref,
            topic_id=target["announcement_id"],
            title=rendered_title,
            message_html=rendered_message_html,
            lock_comment=lock_comment,
        )
        if not isinstance(response, dict):
            response = {}

        updated_result = self.job_repository.record_announcement_edit(
            job_public_id=job_id,
            course_ref=target["course_ref"],
            announcement_id=target["announcement_id"],
            title=rendered_title,
            message_html=rendered_message_html,
            lock_comment=lock_comment,
            canvas_response=response,
        )
        self.job_manager.add_log(
            job_id,
            level="info",
            message="Comunicado editado no Canvas a partir do relatorio.",
            data={
                "course_ref": target["course_ref"],
                "course_id": target["canvas_course_id"] or target["course_id"],
                "announcement_id": target["announcement_id"],
            },
        )

        return {
            "ok": True,
            "message": "Comunicado atualizado no Canvas.",
            "target": self.get_edit_target(job_id, course_ref=target["course_ref"], announcement_id=target["announcement_id"]),
            "course_result": updated_result,
        }

    def _editable_target(self, job_id: str, *, course_ref: str, announcement_id: int | str) -> dict:
        target = self.job_repository.get_announcement_edit_target(
            job_public_id=job_id,
            course_ref=course_ref,
            announcement_id=announcement_id,
        )
        if not target:
            raise ValueError("Comunicado nao encontrado no historico do painel.")
        if target["job_kind"] != "announcement":
            raise ValueError("Somente lotes de comunicados podem ser editados por aqui.")
        if target["row_status"] != "success":
            raise ValueError("Somente comunicados criados com sucesso podem ser editados.")
        if target["dry_run"]:
            raise ValueError("Este registro veio de modo teste e nao criou comunicado real no Canvas.")
        if not target["announcement_id"]:
            raise ValueError("Este resultado nao tem ID de comunicado do Canvas para editar.")
        return target

    def _resolved_edit_content(self, target: dict) -> tuple[str, str, bool]:
        raw_result = target.get("raw_result") or {}
        request_payload = target.get("request_payload") or {}
        title = raw_result.get("title") or request_payload.get("title") or target.get("job_title") or ""
        message_html = raw_result.get("message_html") or request_payload.get("message_html") or ""
        lock_comment = raw_result.get("lock_comment")
        if lock_comment is None:
            lock_comment = bool(request_payload.get("lock_comment"))

        return (
            self._render_template(
                title,
                course_name=target.get("course_name"),
                course_ref=target.get("course_ref"),
                course_code=raw_result.get("course_code"),
            ),
            self._render_template(
                message_html,
                course_name=target.get("course_name"),
                course_ref=target.get("course_ref"),
                course_code=raw_result.get("course_code"),
            ),
            bool(lock_comment),
        )

    def _write_report(self, job_id: str, rows: list[dict]) -> str:
        report_filename = f"announcement-report-{job_id}.csv"
        report_path = Path(self.app_config.reports_dir) / report_filename
        fieldnames = [
            "course_ref",
            "course_id",
            "course_name",
            "course_code",
            "status",
            "title",
            "message_html",
            "lock_comment",
            "announcement_id",
            "announcement_url",
            "published",
            "delayed_post_at",
            "dry_run",
            "attachment_name",
            "error",
        ]

        with report_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

        return report_filename

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
    def _render_template(template: str, **context: str | None) -> str:
        rendered = str(template or "")
        for key, value in context.items():
            rendered = re.sub(r"{{\s*" + re.escape(key) + r"\s*}}", str(value or ""), rendered)
        return rendered
