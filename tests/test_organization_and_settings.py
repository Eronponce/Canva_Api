from __future__ import annotations

import io
import json


class FakeCourseLookupClient:
    def __init__(self):
        self.students = {
            "101": [
                {"id": 11, "name": "Aluno 11"},
                {"id": 22, "name": "Aluno 22"},
            ],
            "202": [
                {"id": 22, "name": "Aluno 22"},
                {"id": 33, "name": "Aluno 33"},
            ],
        }
        self.catalog = [
            {
                "id": 101,
                "name": "Curso 101",
                "course_code": "COD101",
                "workflow_state": "available",
                "term": {"name": "2026/1"},
            },
            {
                "id": 202,
                "name": "Curso 202",
                "course_code": "COD202",
                "workflow_state": "available",
                "term": {"name": "2026/1"},
            },
            {
                "id": 303,
                "name": "Curso 303",
                "course_code": "COD303",
                "workflow_state": "available",
                "term": {"name": "2026/2"},
            },
        ]

    def get_course(self, course_ref):
        return {
            "id": int(course_ref),
            "name": f"Curso {course_ref}",
            "course_code": f"COD{course_ref}",
            "workflow_state": "available",
            "term": {"name": "2026/1"},
        }

    def list_accessible_courses(self):
        return self.catalog

    def list_course_students(self, course_ref):
        return self.students[str(course_ref)]


def test_registered_course_crud_endpoints(app, monkeypatch):
    client = app.test_client()
    monkeypatch.setattr(
        app.extensions["services"]["connection_service"],
        "build_client",
        lambda payload: FakeCourseLookupClient(),
    )

    created = client.post(
        "/api/registered-courses",
        json={
            "course_ref": "4501",
            "base_url": "https://canvas.example.com",
            "access_token": "token",
        },
    )
    assert created.status_code == 201
    assert created.get_json()["item"]["course_ref"] == "4501"
    assert created.get_json()["item"]["course_name"] == "Curso 4501"

    listed = client.get("/api/registered-courses")
    assert listed.status_code == 200
    assert listed.get_json()["items"][0]["course_ref"] == "4501"
    assert listed.get_json()["items"][0]["course_name"] == "Curso 4501"

    deleted = client.delete("/api/registered-courses/4501")
    assert deleted.status_code == 200
    assert deleted.get_json()["ok"] is True

    listed_after_delete = client.get("/api/registered-courses")
    assert listed_after_delete.status_code == 200
    assert listed_after_delete.get_json()["items"] == []


def test_course_catalog_marks_registered_and_bulk_registers_selected(app, monkeypatch):
    client = app.test_client()
    monkeypatch.setattr(
        app.extensions["services"]["connection_service"],
        "build_client",
        lambda payload: FakeCourseLookupClient(),
    )

    created = client.post(
        "/api/registered-courses",
        json={
            "course_ref": "101",
            "base_url": "https://canvas.example.com",
            "access_token": "token",
        },
    )
    assert created.status_code == 201

    catalog = client.post(
        "/api/courses/catalog",
        json={
            "base_url": "https://canvas.example.com",
            "access_token": "token",
            "search_term": "Curso",
        },
    )
    assert catalog.status_code == 200
    items = catalog.get_json()["items"]
    assert len(items) == 3
    by_ref = {item["course_ref"]: item for item in items}
    assert by_ref["101"]["already_registered"] is True
    assert by_ref["202"]["already_registered"] is False

    bulk = client.post(
        "/api/registered-courses/bulk",
        json={
            "base_url": "https://canvas.example.com",
            "access_token": "token",
            "course_refs": ["101", "202", "303", "303"],
        },
    )
    assert bulk.status_code == 201
    payload = bulk.get_json()
    assert payload["created_count"] == 2
    assert payload["updated_count"] == 1
    assert [item["course_ref"] for item in payload["items"]] == ["101", "202", "303"]

    listed = client.get("/api/registered-courses")
    assert listed.status_code == 200
    assert [item["course_ref"] for item in listed.get_json()["items"]] == ["101", "202", "303"]


def test_env_endpoints_save_and_refresh_config(client, isolated_env):
    read_response = client.get("/api/settings/env")
    assert read_response.status_code == 200
    assert "content" in read_response.get_json()
    assert read_response.get_json()["path"] == str(isolated_env["env_file"])

    write_response = client.put(
        "/api/settings/env",
        json={
            "content": "\n".join(
                [
                    "CANVAS_BASE_URL=https://canvas.local.test",
                    "CANVAS_ACCESS_TOKEN=token-local",
                    "HISTORY_LIMIT=55",
                ]
            ),
        },
    )
    assert write_response.status_code == 200

    config_response = client.get("/api/config")
    settings = config_response.get_json()["settings"]
    assert settings["default_base_url"] == "https://canvas.local.test"
    assert settings["env_token_available"] is True
    assert settings["history_limit"] == 55
    assert settings["env_file_path"] == str(isolated_env["env_file"])


def test_app_boot_does_not_create_env_file_when_missing(isolated_env):
    from pathlib import Path

    from src.config import AppConfig

    tmp_root = Path(isolated_env["data_dir"]).parent
    env_path = tmp_root / ".env"
    if env_path.exists():
        env_path.unlink()

    config = AppConfig(
        host="127.0.0.1",
        port=5000,
        debug=False,
        database_url=f"sqlite:///{(tmp_root / 'data' / 'test.db').as_posix()}",
        database_echo=False,
        request_timeout=30,
        retry_max_attempts=4,
        retry_base_delay=1.5,
        history_limit=25,
        legacy_json_import_enabled=False,
        default_base_url="",
        default_access_token="",
        default_token_source="none",
        code_root=tmp_root,
        runtime_root=tmp_root,
        templates_dir=tmp_root,
        static_dir=tmp_root,
        data_dir=tmp_root / "data",
        reports_dir=(tmp_root / "data" / "reports"),
        logs_dir=tmp_root / "logs",
        uploads_dir=(tmp_root / "data" / "uploads"),
        database_file=(tmp_root / "data" / "test.db"),
        history_file=(tmp_root / "data" / "history.json"),
        groups_file=(tmp_root / "data" / "course_groups.json"),
        registered_courses_file=(tmp_root / "data" / "registered_courses.json"),
        env_file=env_path,
        app_log_file=(tmp_root / "logs" / "app.log"),
    )

    config.ensure_runtime_dirs()
    assert env_path.exists() is False


def test_announcement_job_route_resolves_group_ids_into_courses(app, monkeypatch):
    client = app.test_client()
    services = app.extensions["services"]

    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: FakeCourseLookupClient())
    services["course_service"].add_registered_course(
        {"course_ref": "101", "base_url": "https://canvas.example.com", "access_token": "token"}
    )
    services["course_service"].add_registered_course(
        {"course_ref": "202", "base_url": "https://canvas.example.com", "access_token": "token"}
    )
    created_group = services["course_service"].create_group(
        {
            "name": "Grupo A",
            "description": "Primeiro grupo",
            "course_refs": ["101", "202"],
        }
    )["item"]

    captured = {}

    def fake_start_background(job_id, fn, payload):
        captured["job_id"] = job_id
        captured["fn"] = fn
        captured["payload"] = payload

    services["job_manager"].start_background = fake_start_background

    response = client.post(
        "/api/announcements/jobs",
        json={
            "base_url": "https://canvas.example.com",
            "access_token": "token",
            "group_ids": [created_group["id"]],
            "title": "Aviso",
            "message_html": "<p>Teste</p>",
            "publish_mode": "publish_now",
        },
    )

    assert response.status_code == 202
    assert captured["payload"]["course_ids_text"] == "101\n202"
    assert captured["payload"]["course_refs"] == ["101", "202"]


def test_announcement_job_route_accepts_multipart_attachment(app, monkeypatch):
    client = app.test_client()
    services = app.extensions["services"]

    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: FakeCourseLookupClient())
    services["course_service"].add_registered_course(
        {"course_ref": "101", "base_url": "https://canvas.example.com", "access_token": "token"}
    )

    captured = {}

    def fake_start_background(job_id, fn, payload):
        captured["payload"] = payload

    services["job_manager"].start_background = fake_start_background

    response = client.post(
        "/api/announcements/jobs",
        data={
            "payload_json": json.dumps(
                {
                    "base_url": "https://canvas.example.com",
                    "access_token": "token",
                    "target_mode": "courses",
                    "course_refs": ["101"],
                    "title": "Aviso",
                    "message_html": "<p>Teste</p>",
                    "publish_mode": "publish_now",
                }
            ),
            "attachment": (io.BytesIO(b"pdf"), "aviso.pdf"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 202
    assert captured["payload"]["course_ids_text"] == "101"
    assert captured["payload"]["attachment_name"] == "aviso.pdf"
    assert captured["payload"]["attachment_size"] == 3
    assert captured["payload"]["attachment_temp_path"]


def test_message_job_route_resolves_all_groups_without_duplicates(app, monkeypatch):
    client = app.test_client()
    services = app.extensions["services"]

    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: FakeCourseLookupClient())
    for course_ref in ["101", "202", "303"]:
        services["course_service"].add_registered_course(
            {"course_ref": course_ref, "base_url": "https://canvas.example.com", "access_token": "token"}
        )

    services["course_service"].create_group(
        {
            "name": "Grupo A",
            "description": "",
            "course_refs": ["101", "202"],
        }
    )
    services["course_service"].create_group(
        {
            "name": "Grupo B",
            "description": "",
            "course_refs": ["202", "303"],
        }
    )

    captured = {}

    def fake_start_background(job_id, fn, payload):
        captured["payload"] = payload

    services["job_manager"].start_background = fake_start_background

    response = client.post(
        "/api/messages/jobs",
        json={
            "base_url": "https://canvas.example.com",
            "access_token": "token",
            "select_all_groups": True,
            "subject": "Mensagem",
            "message": "Teste",
            "strategy": "users",
        },
    )

    assert response.status_code == 202
    assert captured["payload"]["course_refs"] == ["101", "202", "303"]
    assert captured["payload"]["course_ids_text"] == "101\n202\n303"


def test_groups_include_registered_course_names(app, monkeypatch):
    client = app.test_client()
    services = app.extensions["services"]
    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: FakeCourseLookupClient())

    services["course_service"].add_registered_course(
        {"course_ref": "801", "base_url": "https://canvas.example.com", "access_token": "token"}
    )
    created_group = services["course_service"].create_group(
        {
            "name": "Grupo Nomeado",
            "description": "",
            "course_refs": ["801"],
        }
    )["item"]

    response = client.get(f"/api/groups/{created_group['id']}")
    assert response.status_code == 200
    item = response.get_json()["item"]
    assert item["courses"][0]["course_name"] == "Curso 801"


def test_message_recipients_route_lists_unique_students(app, monkeypatch):
    client = app.test_client()
    services = app.extensions["services"]
    monkeypatch.setattr(
        services["connection_service"],
        "build_client",
        lambda payload: FakeCourseLookupClient(),
    )

    response = client.post(
        "/api/messages/recipients",
        json={
            "base_url": "https://canvas.example.com",
            "access_token": "token",
            "course_refs": ["101", "202"],
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["unique_recipients"] == 3
    assert payload["total_students_found"] == 4
    shared = next(item for item in payload["items"] if item["user_id"] == 22)
    assert shared["course_refs"] == ["101", "202"]


def test_reports_analytics_endpoint_returns_collapsible_sections_shape(app):
    client = app.test_client()
    services = app.extensions["services"]
    course_repository = services["course_service"].course_repository

    course_repository.upsert_course({"course_ref": "101", "course_name": "Curso 101", "source_type": "test_seed"})
    course_repository.upsert_course({"course_ref": "202", "course_name": "Curso 202", "source_type": "test_seed"})
    group = services["course_service"].create_group(
        {"name": "Grupo Analitico", "description": "", "course_refs": ["101", "202"]}
    )["item"]

    announcement_job = services["job_manager"].create_job(
        kind="announcement",
        title="Aviso Analitico",
        summary={"course_refs": ["101"], "group_ids": [group["id"]]},
    )
    services["job_manager"].complete(
        announcement_job["id"],
        result={
            "summary": {"success_count": 1, "failure_count": 0},
            "course_results": [
                {
                    "course_ref": "101",
                    "course_id": 101,
                    "course_name": "Curso 101",
                    "status": "success",
                    "announcement_id": 9991,
                    "recipients_sent": 0,
                }
            ],
        },
    )

    message_job = services["job_manager"].create_job(
        kind="message",
        title="Mensagem Analitica",
        summary={"course_refs": ["202"], "group_ids": [group["id"]]},
        requested_strategy="users",
        dedupe=True,
    )
    services["job_manager"].complete(
        message_job["id"],
        result={
            "summary": {"success_count": 0, "failure_count": 1},
            "course_results": [
                {
                    "course_ref": "202",
                    "course_id": 202,
                    "course_name": "Curso 202",
                    "status": "error",
                    "strategy_requested": "users",
                    "strategy_used": "users",
                    "students_found": 12,
                    "recipients_targeted": 12,
                    "recipients_sent": 8,
                    "error": "Falha simulada",
                }
            ],
        },
    )

    response = client.get("/api/reports/analytics?days=30")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["overview"]["total_jobs"] == 2
    assert "operational" in payload["sections"]
    assert "top_courses" in payload["sections"]
    assert "recent_failures" in payload["sections"]
    assert payload["sections"]["top_groups"]["items"][0]["group_name"] == "Grupo Analitico"


def test_database_wipe_endpoint_hard_deletes_everything(app, monkeypatch):
    client = app.test_client()
    services = app.extensions["services"]
    monkeypatch.setattr(
        services["connection_service"],
        "build_client",
        lambda payload: FakeCourseLookupClient(),
    )

    services["course_service"].add_registered_course(
        {"course_ref": "901", "base_url": "https://canvas.example.com", "access_token": "token"}
    )
    group = services["course_service"].create_group(
        {"name": "Grupo Wipe", "description": "", "course_refs": ["901"]}
    )["item"]
    job = services["job_manager"].create_job(
        kind="announcement",
        title="Job para limpar",
        summary={"course_refs": ["901"], "group_ids": [group["id"]]},
    )
    services["job_manager"].complete(
        job["id"],
        result={
            "summary": {"success_count": 1},
            "course_results": [
                {
                    "course_ref": "901",
                    "course_id": 901,
                    "course_name": "Curso 901",
                    "status": "success",
                    "announcement_id": 11,
                }
            ],
        },
    )

    invalid = client.post("/api/settings/database/wipe", json={"confirmation_text": "APAGAR"})
    assert invalid.status_code == 400

    response = client.post("/api/settings/database/wipe", json={"confirmation_text": "EXCLUIR"})
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["ok"] is True
    assert payload["deleted_counts"]["courses"] >= 1
    assert payload["deleted_counts"]["course_groups"] >= 1
    assert payload["deleted_counts"]["job_runs"] >= 1

    config_response = client.get("/api/config")
    config_payload = config_response.get_json()
    assert config_payload["registered_courses"] == []
    assert config_payload["groups"] == []

    history_response = client.get("/api/history")
    assert history_response.status_code == 200
    assert history_response.get_json()["items"] == []
