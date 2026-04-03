from __future__ import annotations


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

    def get_course(self, course_ref):
        return {
            "id": int(course_ref),
            "name": f"Curso {course_ref}",
            "course_code": f"COD{course_ref}",
            "workflow_state": "available",
            "term": {"name": "2026/1"},
        }

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


def test_env_endpoints_save_and_refresh_config(client):
    read_response = client.get("/api/settings/env")
    assert read_response.status_code == 200
    assert "content" in read_response.get_json()

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
        request_timeout=30,
        retry_max_attempts=4,
        retry_base_delay=1.5,
        history_limit=25,
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
            "group_ids": [created_group["id"]],
            "title": "Aviso",
            "message_html": "<p>Teste</p>",
            "publish_mode": "publish_now",
        },
    )

    assert response.status_code == 202
    assert captured["payload"]["course_ids_text"] == "101\n202"
    assert captured["payload"]["course_refs"] == ["101", "202"]


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
