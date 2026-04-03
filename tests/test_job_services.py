from __future__ import annotations

from pathlib import Path


class FakeCanvasClient:
    def __init__(self):
        self.current_user = {"id": 77, "name": "Usuário Teste"}
        self.courses = {
            "101": {
                "id": 101,
                "name": "Cálculo I",
                "course_code": "MAT101",
                "workflow_state": "available",
                "term": {"name": "2026/1"},
            },
            "202": {
                "id": 202,
                "name": "Física I",
                "course_code": "FIS202",
                "workflow_state": "available",
                "term": {"name": "2026/1"},
            },
            "303": {
                "id": 303,
                "name": "Algoritmos",
                "course_code": "ALG303",
                "workflow_state": "available",
                "term": {"name": "2026/1"},
            },
        }
        self.students = {
            "101": [{"id": 1, "name": "Aluno 1"}, {"id": 2, "name": "Aluno 2"}],
            "202": [{"id": 2, "name": "Aluno 2"}, {"id": 3, "name": "Aluno 3"}],
        }
        self.announcements_created = []
        self.conversations_created = []

    def get_current_user(self):
        return self.current_user

    def get_course(self, course_ref):
        course_ref = str(course_ref)
        if course_ref == "999":
            raise Exception("Curso não encontrado")
        return self.courses[course_ref]

    def create_announcement(self, **kwargs):
        self.announcements_created.append(kwargs)
        course_ref = str(kwargs["course_ref"])
        return {
            "id": 5000 + int(course_ref),
            "html_url": f"https://canvas.example.com/courses/{course_ref}/discussion_topics/{5000 + int(course_ref)}",
            "published": kwargs["published"],
        }

    def list_course_students(self, course_ref):
        return self.students[str(course_ref)]

    def find_messageable_context(self, *, course_id, course_name):
        return {"id": f"course_{course_id}", "name": course_name}

    def create_conversation(self, **kwargs):
        self.conversations_created.append(kwargs)
        return [{"id": 9000 + len(self.conversations_created)}]


def test_announcement_job_creates_report_and_history(app, monkeypatch):
    services = app.extensions["services"]
    fake_client = FakeCanvasClient()
    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: fake_client)

    job_manager = services["job_manager"]
    service = services["announcement_service"]
    job = job_manager.create_job(kind="announcement", title="Aviso teste")

    service.run_job(
        job["id"],
        {
            "base_url": "https://canvas.example.com",
            "access_token": "token",
            "course_ids_text": "101\n202",
            "title": "Prova 1",
            "message_html": "<p>Estudem</p>",
            "publish_mode": "publish_now",
            "lock_comment": True,
            "dry_run": False,
        },
    )

    finished = job_manager.get_job(job["id"])
    assert finished["status"] == "completed"
    assert finished["result"]["summary"]["success_count"] == 2
    assert len(fake_client.announcements_created) == 2
    report_path = Path(app.config["APP_CONFIG"].reports_dir) / finished["report_filename"]
    assert report_path.exists()


def test_announcement_job_handles_course_failure(app, monkeypatch):
    services = app.extensions["services"]
    fake_client = FakeCanvasClient()
    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: fake_client)

    job_manager = services["job_manager"]
    service = services["announcement_service"]
    job = job_manager.create_job(kind="announcement", title="Aviso com falha")

    service.run_job(
        job["id"],
        {
            "base_url": "https://canvas.example.com",
            "access_token": "token",
            "course_ids_text": "101\n999",
            "title": "Atenção",
            "message_html": "<p>Mensagem</p>",
            "publish_mode": "publish_now",
            "lock_comment": False,
            "dry_run": False,
        },
    )

    finished = job_manager.get_job(job["id"])
    assert finished["status"] == "completed"
    assert finished["result"]["summary"]["failure_count"] == 1
    rows = finished["result"]["course_results"]
    assert any(row["status"] == "error" for row in rows)


def test_message_job_deduplicates_students_in_dry_run(app, monkeypatch):
    services = app.extensions["services"]
    fake_client = FakeCanvasClient()
    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: fake_client)

    job_manager = services["job_manager"]
    service = services["message_service"]
    job = job_manager.create_job(kind="message", title="Mensagem teste")

    service.run_job(
        job["id"],
        {
            "base_url": "https://canvas.example.com",
            "access_token": "token",
            "course_ids_text": "101\n202",
            "subject": "Lembrete",
            "message": "Mensagem de teste",
            "strategy": "users",
            "dedupe": True,
            "dry_run": True,
        },
    )

    finished = job_manager.get_job(job["id"])
    summary = finished["result"]["summary"]
    assert finished["status"] == "completed"
    assert summary["total_students_found"] == 4
    assert summary["total_recipients_targeted"] == 3
    assert summary["total_duplicates_skipped"] == 1
    assert summary["dry_run"] is True


def test_message_job_filters_manual_recipients_and_falls_back_from_context(app, monkeypatch):
    services = app.extensions["services"]
    fake_client = FakeCanvasClient()
    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: fake_client)

    job_manager = services["job_manager"]
    service = services["message_service"]
    job = job_manager.create_job(kind="message", title="Mensagem manual")

    service.run_job(
        job["id"],
        {
            "base_url": "https://canvas.example.com",
            "access_token": "token",
            "course_ids_text": "101\n202",
            "subject": "Aviso",
            "message": "Mensagem manual",
            "strategy": "context",
            "dedupe": True,
            "dry_run": True,
            "manual_recipients": True,
            "selected_user_ids": [2],
        },
    )

    finished = job_manager.get_job(job["id"])
    summary = finished["result"]["summary"]
    rows = finished["result"]["course_results"]

    assert finished["status"] == "completed"
    assert summary["manual_recipients"] is True
    assert summary["selected_user_count"] == 1
    assert summary["effective_strategy"] == "users"
    assert summary["total_recipients_targeted"] == 1
    assert rows[0]["manual_matches"] == 1
    assert rows[0]["recipients_targeted"] == 1
    assert rows[1]["manual_matches"] == 1
    assert rows[1]["recipients_targeted"] == 0
    assert rows[1]["status"] == "skipped"
