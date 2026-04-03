from __future__ import annotations


class FakeCanvasClient:
    def __init__(self):
        self.current_user = {"id": 77, "name": "UsuÃ¡rio Teste"}
        self.courses = {
            "101": {
                "id": 101,
                "name": "CÃ¡lculo I",
                "course_code": "MAT101",
                "workflow_state": "available",
                "term": {"name": "2026/1"},
            },
        }
        self.students = {
            "101": [{"id": 1, "name": "Aluno 1"}, {"id": 2, "name": "Aluno 2"}],
        }
        self.conversations_created = []

    def get_current_user(self):
        return self.current_user

    def get_course(self, course_ref):
        return self.courses[str(course_ref)]

    def list_course_students(self, course_ref):
        return self.students[str(course_ref)]

    def find_messageable_context(self, *, course_id, course_name):
        return {"id": f"course_{course_id}", "name": course_name}

    def create_conversation(self, **kwargs):
        self.conversations_created.append(kwargs)
        return [{"id": 9000 + len(self.conversations_created)}]


def test_message_job_renders_student_name_and_sends_individually(app, monkeypatch):
    services = app.extensions["services"]
    fake_client = FakeCanvasClient()
    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: fake_client)

    job_manager = services["job_manager"]
    service = services["message_service"]
    job = job_manager.create_job(kind="message", title="Mensagem personalizada")

    service.run_job(
        job["id"],
        {
            "base_url": "https://canvas.example.com",
            "access_token": "token",
            "course_ids_text": "101",
            "subject": "Aviso para {{student_name}}",
            "message": "Ola {{student_name}}, bem-vindo(a) em {{course_name}}",
            "strategy": "context",
            "dedupe": False,
            "dry_run": False,
        },
    )

    finished = job_manager.get_job(job["id"])
    assert finished["status"] == "completed"
    assert finished["result"]["summary"]["effective_strategy"] == "users_personalized"
    assert len(fake_client.conversations_created) == 2
    assert fake_client.conversations_created[0]["recipients"] == [1]
    assert fake_client.conversations_created[0]["subject"] == "Aviso para Aluno 1"
    assert fake_client.conversations_created[0]["body"] == "Ola Aluno 1, bem-vindo(a) em CÃ¡lculo I"
    assert fake_client.conversations_created[1]["recipients"] == [2]
    assert fake_client.conversations_created[1]["subject"] == "Aviso para Aluno 2"
