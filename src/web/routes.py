from __future__ import annotations

import json

from flask import Blueprint, current_app, jsonify, render_template, request, send_from_directory

from src.services.canvas_client import CanvasApiError
from src.utils.attachment_utils import save_uploaded_file


web = Blueprint("web", __name__)


def services():
    return current_app.extensions["services"]


def _request_payload() -> dict:
    if request.is_json:
        return request.get_json(silent=True) or {}

    raw_payload = request.form.get("payload_json", "")
    if raw_payload:
        try:
            return json.loads(raw_payload)
        except json.JSONDecodeError as exc:
            raise ValueError("Nao foi possivel interpretar os dados enviados pelo formulario.") from exc
    return {}


def _request_attachment() -> dict | None:
    uploaded_file = request.files.get("attachment")
    if not uploaded_file or not uploaded_file.filename:
        return None
    app_config = current_app.config["APP_CONFIG"]
    return save_uploaded_file(uploaded_file, app_config.uploads_dir)


def _with_resolved_courses(payload: dict, empty_message: str) -> tuple[dict, list[str]]:
    course_service = services()["course_service"]
    course_refs = course_service.resolve_payload_course_refs(payload)
    if not course_refs:
        raise ValueError(empty_message)

    hydrated_payload = dict(payload)
    hydrated_payload["course_refs"] = course_refs
    hydrated_payload["course_ids_text"] = "\n".join(course_refs)
    return hydrated_payload, course_refs


def _include_inactive() -> bool:
    return str(request.args.get("include_inactive", "")).strip().lower() in {"1", "true", "yes"}


def _job_group_ids(raw_payload: dict) -> list[str]:
    course_service = services()["course_service"]
    if bool(raw_payload.get("select_all_groups")):
        return [item["id"] for item in course_service.list_groups()["items"]]
    return [str(item).strip() for item in (raw_payload.get("group_ids") or []) if str(item).strip()]


def _safe_request_payload(payload: dict) -> dict:
    sanitized = dict(payload)
    sanitized.pop("access_token", None)
    sanitized.pop("api_token", None)
    return sanitized


@web.get("/")
def index():
    return render_template("index.html")


@web.get("/api/config")
def get_config():
    app_config = current_app.config["APP_CONFIG"]
    course_service = services()["course_service"]
    return jsonify(
        {
            "settings": app_config.public_settings(),
            "groups": course_service.list_groups()["items"],
            "registered_courses": course_service.list_registered_courses()["items"],
            "announcement_recurrences": services()["announcement_recurrence_service"].list_recurrences(include_inactive=True)["items"],
        }
    )


@web.post("/api/connection/test")
def test_connection():
    payload = request.get_json(silent=True) or {}
    result = services()["connection_service"].test_connection(payload)
    return jsonify(result)


@web.post("/api/courses/resolve")
def resolve_courses():
    payload = request.get_json(silent=True) or {}
    result = services()["course_service"].resolve_courses(payload)
    return jsonify(result)


@web.post("/api/courses/catalog")
def course_catalog():
    payload = request.get_json(silent=True) or {}
    result = services()["course_service"].list_catalog(payload)
    return jsonify(result)


@web.get("/api/registered-courses")
def list_registered_courses():
    return jsonify(services()["course_service"].list_registered_courses(include_inactive=_include_inactive()))


@web.post("/api/registered-courses")
def create_registered_course():
    payload = request.get_json(silent=True) or {}
    result = services()["course_service"].add_registered_course(payload)
    return jsonify(result), 201


@web.post("/api/registered-courses/bulk")
def create_registered_courses_bulk():
    payload = request.get_json(silent=True) or {}
    result = services()["course_service"].add_registered_courses(payload)
    return jsonify(result), 201


@web.delete("/api/registered-courses/<path:course_ref>")
def delete_registered_course(course_ref: str):
    result = services()["course_service"].delete_registered_course(course_ref)
    return jsonify(result)


@web.patch("/api/registered-courses/<path:course_ref>/reactivate")
def reactivate_registered_course(course_ref: str):
    result = services()["course_service"].reactivate_registered_course(course_ref)
    return jsonify(result)


@web.get("/api/groups")
def list_groups():
    return jsonify(services()["course_service"].list_groups(include_inactive=_include_inactive()))


@web.get("/api/groups/<group_id>")
def get_group(group_id: str):
    return jsonify(services()["course_service"].get_group(group_id, include_inactive=_include_inactive()))


@web.post("/api/groups")
def create_group():
    payload = request.get_json(silent=True) or {}
    result = services()["course_service"].create_group(payload)
    return jsonify(result), 201


@web.put("/api/groups/<group_id>")
def update_group(group_id: str):
    payload = request.get_json(silent=True) or {}
    result = services()["course_service"].update_group(group_id, payload)
    return jsonify(result)


@web.delete("/api/groups/<group_id>")
def delete_group(group_id: str):
    result = services()["course_service"].delete_group(group_id)
    return jsonify(result)


@web.patch("/api/groups/<group_id>/reactivate")
def reactivate_group(group_id: str):
    result = services()["course_service"].reactivate_group(group_id)
    return jsonify(result)


@web.get("/api/settings/env")
def read_env_file():
    return jsonify(services()["env_service"].read_env())


@web.put("/api/settings/env")
def save_env_file():
    payload = request.get_json(silent=True) or {}
    result = services()["env_service"].save_env(payload.get("content", ""))
    return jsonify(result)


@web.post("/api/settings/database/wipe")
def wipe_database():
    payload = request.get_json(silent=True) or {}
    confirmation_text = str(payload.get("confirmation_text") or "").strip().upper()
    if confirmation_text != "EXCLUIR":
        raise ValueError("Digite EXCLUIR para confirmar a limpeza total do banco.")

    deleted_counts = services()["database_admin_repository"].wipe_all_data()
    return jsonify(
        {
            "ok": True,
            "message": "Banco limpo com sucesso.",
            "deleted_counts": deleted_counts,
        }
    )


@web.post("/api/announcements/jobs")
def create_announcement_job():
    raw_payload = _request_payload()
    attachment = _request_attachment()
    if attachment:
        raw_payload = {
            **raw_payload,
            "attachment_temp_path": attachment["temp_path"],
            "attachment_name": attachment["original_name"],
            "attachment_content_type": attachment["content_type"],
            "attachment_size": attachment["size"],
        }
    payload, course_refs = _with_resolved_courses(
        raw_payload,
        "Selecione ao menos um grupo ou curso para publicar o comunicado.",
    )
    credentials = services()["connection_service"].resolve_credentials(raw_payload)
    title = (payload.get("title") or "Comunicado em lote").strip()
    job_manager = services()["job_manager"]
    job = job_manager.create_job(
        kind="announcement",
        title=title,
        base_url=credentials["base_url"],
        request_payload=_safe_request_payload(payload),
        request_token_source="inline" if (raw_payload.get("access_token") or raw_payload.get("api_token")) else services()["connection_service"].app_config.default_token_source,
        dry_run=bool(payload.get("dry_run")),
        summary={
            "course_refs": course_refs,
            "group_ids": _job_group_ids(raw_payload),
            "select_all_groups": bool(raw_payload.get("select_all_groups")),
        },
    )
    job_manager.start_background(
        job["id"],
        services()["announcement_service"].run_job,
        payload,
    )
    return jsonify({"job": job}), 202


@web.post("/api/announcements/preflight")
def preview_announcement_job():
    raw_payload = _request_payload()
    uploaded_file = request.files.get("attachment")
    if uploaded_file and uploaded_file.filename:
        raw_payload = {
            **raw_payload,
            "attachment_name": uploaded_file.filename,
            "attachment_content_type": uploaded_file.mimetype or "application/octet-stream",
            "attachment_size": getattr(uploaded_file, "content_length", None) or 0,
        }
    payload, _course_refs = _with_resolved_courses(
        raw_payload,
        "Selecione ao menos um grupo ou curso para revisar o comunicado.",
    )
    result = services()["announcement_service"].preview_job(payload)
    return jsonify(result)


@web.post("/api/messages/jobs")
def create_message_job():
    raw_payload = _request_payload()
    attachment = _request_attachment()
    if attachment:
        raw_payload = {
            **raw_payload,
            "attachment_temp_path": attachment["temp_path"],
            "attachment_name": attachment["original_name"],
            "attachment_content_type": attachment["content_type"],
            "attachment_size": attachment["size"],
        }
    payload, course_refs = _with_resolved_courses(
        raw_payload,
        "Selecione ao menos um grupo ou curso para enviar as mensagens.",
    )
    credentials = services()["connection_service"].resolve_credentials(raw_payload)
    title = (payload.get("subject") or "Mensagem em lote").strip()
    job_manager = services()["job_manager"]
    job = job_manager.create_job(
        kind="message",
        title=title,
        base_url=credentials["base_url"],
        request_payload=_safe_request_payload(payload),
        request_token_source="inline" if (raw_payload.get("access_token") or raw_payload.get("api_token")) else services()["connection_service"].app_config.default_token_source,
        requested_strategy=(payload.get("strategy") or "users"),
        dry_run=bool(payload.get("dry_run")),
        dedupe=bool(payload.get("dedupe")),
        summary={
            "course_refs": course_refs,
            "group_ids": _job_group_ids(raw_payload),
            "select_all_groups": bool(raw_payload.get("select_all_groups")),
        },
    )
    job_manager.start_background(
        job["id"],
        services()["message_service"].run_job,
        payload,
    )
    return jsonify({"job": job}), 202


@web.post("/api/messages/recipients")
def preview_message_recipients():
    raw_payload = request.get_json(silent=True) or {}
    payload, _course_refs = _with_resolved_courses(
        raw_payload,
        "Selecione ao menos um grupo ou curso para listar os destinatarios.",
    )
    result = services()["message_service"].preview_recipients(payload)
    return jsonify(result)


@web.post("/api/engagement/inactive-targets")
def preview_engagement_targets():
    raw_payload = request.get_json(silent=True) or {}
    payload, course_refs = _with_resolved_courses(
        raw_payload,
        "Selecione ao menos um grupo ou curso para a busca ativa.",
    )
    result = services()["engagement_service"].preview_targets(payload)
    if bool(raw_payload.get("save_report")):
        credentials = services()["connection_service"].resolve_credentials(raw_payload)
        criteria_modes = payload.get("criteria_modes") or []
        job_manager = services()["job_manager"]
        job = job_manager.create_job(
            kind="engagement",
            title="Previa de inativos",
            base_url=credentials["base_url"],
            request_payload=_safe_request_payload(payload),
            request_token_source="inline" if (raw_payload.get("access_token") or raw_payload.get("api_token")) else services()["connection_service"].app_config.default_token_source,
            requested_strategy=",".join(criteria_modes) or (payload.get("criteria_mode") or "never_accessed,low_total_activity"),
            effective_strategy="preview_only",
            dry_run=True,
            dedupe=False,
            summary={
                "course_refs": course_refs,
                "group_ids": _job_group_ids(raw_payload),
                "select_all_groups": bool(raw_payload.get("select_all_groups")),
                "preview_only": True,
            },
        )
        try:
            result["report_job"] = services()["engagement_service"].complete_preview_report(job["id"], payload, result)
        except Exception as exc:  # noqa: BLE001
            job_manager.fail(job["id"], str(exc))
            raise
    return jsonify(result)


@web.post("/api/engagement/jobs")
def create_engagement_job():
    raw_payload = request.get_json(silent=True) or {}
    payload, course_refs = _with_resolved_courses(
        raw_payload,
        "Selecione ao menos um grupo ou curso para a busca ativa.",
    )
    credentials = services()["connection_service"].resolve_credentials(raw_payload)
    title = (payload.get("subject") or "Busca ativa").strip()
    job_manager = services()["job_manager"]
    job = job_manager.create_job(
        kind="engagement",
        title=title,
        base_url=credentials["base_url"],
        request_payload=_safe_request_payload(payload),
        request_token_source="inline" if (raw_payload.get("access_token") or raw_payload.get("api_token")) else services()["connection_service"].app_config.default_token_source,
        requested_strategy=",".join(payload.get("criteria_modes") or []) or (payload.get("criteria_mode") or "never_accessed,low_total_activity"),
        effective_strategy="individual_users",
        dry_run=bool(payload.get("dry_run")),
        dedupe=False,
        summary={
            "course_refs": course_refs,
            "group_ids": _job_group_ids(raw_payload),
            "select_all_groups": bool(raw_payload.get("select_all_groups")),
        },
    )
    job_manager.start_background(
        job["id"],
        services()["engagement_service"].run_job,
        payload,
    )
    return jsonify({"job": job}), 202


@web.post("/api/announcement-recurrences/preview")
def preview_announcement_recurrence():
    raw_payload = request.get_json(silent=True) or {}
    result = services()["announcement_recurrence_service"].preview(raw_payload)
    return jsonify(result)


@web.get("/api/announcement-recurrences")
def list_announcement_recurrences():
    return jsonify(services()["announcement_recurrence_service"].list_recurrences(include_inactive=_include_inactive()))


@web.get("/api/announcement-recurrences/<recurrence_id>")
def get_announcement_recurrence(recurrence_id: str):
    return jsonify(services()["announcement_recurrence_service"].get_recurrence(recurrence_id, include_inactive=_include_inactive()))


@web.post("/api/announcement-recurrences")
def create_announcement_recurrence():
    raw_payload = request.get_json(silent=True) or {}
    result = services()["announcement_recurrence_service"].create_recurrence(raw_payload)
    return jsonify(result), 201


@web.put("/api/announcement-recurrences/<recurrence_id>")
def update_announcement_recurrence(recurrence_id: str):
    raw_payload = request.get_json(silent=True) or {}
    result = services()["announcement_recurrence_service"].update_recurrence(recurrence_id, raw_payload)
    return jsonify(result)


@web.post("/api/announcement-recurrences/<recurrence_id>/cancel")
def cancel_announcement_recurrence(recurrence_id: str):
    raw_payload = request.get_json(silent=True) or {}
    result = services()["announcement_recurrence_service"].cancel_recurrence(recurrence_id, raw_payload)
    return jsonify(result)


@web.get("/api/jobs/<job_id>")
def get_job(job_id: str):
    job = services()["job_manager"].get_job(job_id)
    if not job:
        return jsonify({"error": "Job nao encontrado."}), 404
    return jsonify(job)


@web.get("/api/history")
def list_history():
    history = services()["job_manager"].list_history()
    return jsonify({"items": history})


@web.get("/api/reports/analytics")
def analytics_report():
    raw_days = str(request.args.get("days", "30")).strip()
    try:
        days = max(int(raw_days), 1)
    except ValueError as exc:
        raise ValueError("Informe um periodo valido em dias para os relatorios.") from exc
    report = services()["report_repository"].analytics(days=days)
    return jsonify(report)


@web.get("/api/history/<job_id>")
def get_history_item(job_id: str):
    item = services()["job_manager"].get_job(job_id)
    if not item:
        return jsonify({"error": "Historico nao encontrado."}), 404
    return jsonify(item)


@web.get("/api/history/<job_id>/csv")
def download_csv(job_id: str):
    app_config = current_app.config["APP_CONFIG"]
    item = services()["job_manager"].get_job(job_id)
    if not item or not item.get("report_filename"):
        return jsonify({"error": "Relatorio CSV nao encontrado para este job."}), 404
    return send_from_directory(
        app_config.reports_dir,
        item["report_filename"],
        as_attachment=True,
    )


@web.get("/api/history/<job_id>/announcements/<announcement_id>/edit")
def get_history_announcement_edit_target(job_id: str, announcement_id: str):
    course_ref = str(request.args.get("course_ref") or "").strip()
    result = services()["announcement_service"].get_edit_target(
        job_id,
        course_ref=course_ref,
        announcement_id=announcement_id,
    )
    return jsonify(result)


@web.put("/api/history/<job_id>/announcements/<announcement_id>")
def update_history_announcement(job_id: str, announcement_id: str):
    payload = request.get_json(silent=True) or {}
    result = services()["announcement_service"].update_history_announcement(
        job_id,
        announcement_id=announcement_id,
        payload=payload,
    )
    return jsonify(result)


def register_error_handlers(app) -> None:
    @app.errorhandler(ValueError)
    def handle_value_error(exc):  # noqa: ANN001
        return jsonify({"error": str(exc)}), 400

    @app.errorhandler(CanvasApiError)
    def handle_canvas_error(exc):  # noqa: ANN001
        status = 502 if exc.status_code is None or exc.status_code >= 500 else exc.status_code
        return jsonify({"error": exc.message, "details": exc.details}), status

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc):  # noqa: ANN001
        current_app.logger.exception("Erro inesperado: %s", exc)
        return jsonify({"error": "Erro interno inesperado."}), 500
