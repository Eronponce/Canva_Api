from __future__ import annotations

from flask import Blueprint, current_app, jsonify, render_template, request, send_from_directory

from src.services.canvas_client import CanvasApiError


web = Blueprint("web", __name__)


def services():
    return current_app.extensions["services"]


def _with_resolved_courses(payload: dict, empty_message: str) -> tuple[dict, list[str]]:
    course_service = services()["course_service"]
    course_refs = course_service.resolve_payload_course_refs(payload)
    if not course_refs:
        raise ValueError(empty_message)

    hydrated_payload = dict(payload)
    hydrated_payload["course_refs"] = course_refs
    hydrated_payload["course_ids_text"] = "\n".join(course_refs)
    return hydrated_payload, course_refs


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
    return jsonify(services()["course_service"].list_registered_courses())


@web.post("/api/registered-courses")
def create_registered_course():
    payload = request.get_json(silent=True) or {}
    result = services()["course_service"].add_registered_course(payload)
    return jsonify(result), 201


@web.delete("/api/registered-courses/<path:course_ref>")
def delete_registered_course(course_ref: str):
    result = services()["course_service"].delete_registered_course(course_ref)
    return jsonify(result)


@web.get("/api/groups")
def list_groups():
    return jsonify(services()["course_service"].list_groups())


@web.get("/api/groups/<group_id>")
def get_group(group_id: str):
    return jsonify(services()["course_service"].get_group(group_id))


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


@web.get("/api/settings/env")
def read_env_file():
    return jsonify(services()["env_service"].read_env())


@web.put("/api/settings/env")
def save_env_file():
    payload = request.get_json(silent=True) or {}
    result = services()["env_service"].save_env(payload.get("content", ""))
    return jsonify(result)


@web.post("/api/announcements/jobs")
def create_announcement_job():
    raw_payload = request.get_json(silent=True) or {}
    payload, course_refs = _with_resolved_courses(
        raw_payload,
        "Selecione ao menos um grupo ou curso para publicar o comunicado.",
    )
    title = (payload.get("title") or "Comunicado em lote").strip()
    job_manager = services()["job_manager"]
    job = job_manager.create_job(
        kind="announcement",
        title=title,
        summary={
            "course_refs": course_refs,
            "group_ids": raw_payload.get("group_ids", []),
            "select_all_groups": bool(raw_payload.get("select_all_groups")),
        },
    )
    job_manager.start_background(
        job["id"],
        services()["announcement_service"].run_job,
        payload,
    )
    return jsonify({"job": job}), 202


@web.post("/api/messages/jobs")
def create_message_job():
    raw_payload = request.get_json(silent=True) or {}
    payload, course_refs = _with_resolved_courses(
        raw_payload,
        "Selecione ao menos um grupo ou curso para enviar as mensagens.",
    )
    title = (payload.get("subject") or "Mensagem em lote").strip()
    job_manager = services()["job_manager"]
    job = job_manager.create_job(
        kind="message",
        title=title,
        summary={
            "course_refs": course_refs,
            "group_ids": raw_payload.get("group_ids", []),
            "select_all_groups": bool(raw_payload.get("select_all_groups")),
        },
    )
    job_manager.start_background(
        job["id"],
        services()["message_service"].run_job,
        payload,
    )
    return jsonify({"job": job}), 202


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
