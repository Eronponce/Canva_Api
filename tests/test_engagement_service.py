from __future__ import annotations


class FakeEngagementClient:
    def __init__(self):
        self.conversation_id = 9000
        self.students = {
            "101": [
                {"id": 11, "name": "Aluno Zero"},
                {"id": 22, "name": "Aluno Modulo"},
                {"id": 33, "name": "Aluno Ativo"},
            ]
        }
        self.analytics = {
            "101": [
                {"id": 11, "page_views": 0, "participations": 0},
                {"id": 22, "page_views": 5, "participations": 1},
                {"id": 33, "page_views": 12, "participations": 4},
            ]
        }
        self.progress = {
            "101": [
                {
                    "id": 11,
                    "progress": {
                        "requirement_count": 3,
                        "requirement_completed_count": 0,
                        "next_requirement_url": "https://canvas.example.com/courses/101/modules/items/1",
                        "completed_at": None,
                    },
                },
                {
                    "id": 22,
                    "progress": {
                        "requirement_count": 3,
                        "requirement_completed_count": 1,
                        "next_requirement_url": "https://canvas.example.com/courses/101/modules/items/2",
                        "completed_at": None,
                    },
                },
                {
                    "id": 33,
                    "progress": {
                        "requirement_count": 3,
                        "requirement_completed_count": 3,
                        "next_requirement_url": None,
                        "completed_at": "2026-04-03T02:00:00Z",
                    },
                },
            ]
        }

    def get_current_user(self):
        return {"id": 999, "name": "Docente Teste"}

    def get_course(self, course_ref):
        return {
            "id": int(course_ref),
            "name": f"Curso {course_ref}",
            "course_code": f"COD{course_ref}",
            "term": {"name": "2026/1"},
            "workflow_state": "available",
        }

    def list_course_students(self, course_ref):
        return self.students[str(course_ref)]

    def list_course_student_summaries(self, course_ref, student_id=None):
        items = self.analytics[str(course_ref)]
        if student_id is None:
            return items
        return [item for item in items if int(item["id"]) == int(student_id)]

    def get_bulk_user_progress(self, course_ref):
        return self.progress[str(course_ref)]

    def create_conversation(self, *, recipients, subject, body, context_code=None, force_new=True, group_conversation=False, mode=None, extra_params=None):
        self.conversation_id += 1
        return {"id": self.conversation_id, "subject": subject, "body": body, "context_code": context_code, "recipients": recipients}


def _seed_courses(client, *course_refs: str) -> None:
    course_repository = client.application.extensions["services"]["course_service"].course_repository
    for course_ref in course_refs:
        course_repository.upsert_course(
            {
                "course_ref": course_ref,
                "course_name": f"Curso {course_ref}",
                "course_code": f"COD{course_ref}",
                "source_type": "test_seed",
            }
        )


def test_engagement_preview_returns_inactive_and_incomplete_students(app, monkeypatch):
    client = app.test_client()
    fake_client = FakeEngagementClient()
    monkeypatch.setattr(
        app.extensions["services"]["connection_service"],
        "build_client",
        lambda payload: fake_client,
    )
    _seed_courses(client, "101")

    response = client.post(
        "/api/engagement/inactive-targets",
        json={
            "base_url": "https://canvas.example.com",
            "access_token": "token",
            "course_refs": ["101"],
            "criteria_mode": "never_accessed_or_incomplete_resources",
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["total_courses"] == 1
    assert payload["summary"]["total_students_found"] == 3
    assert payload["summary"]["total_matched_students"] == 2
    assert payload["summary"]["total_never_accessed_matches"] == 1
    assert payload["summary"]["total_incomplete_resources_matches"] == 2
    assert payload["summary"]["top_priority_course_name"] == "Curso 101"
    assert payload["courses"][0]["matched_students"] == 2
    assert payload["courses"][0]["priority_level"] in {"alta", "critica"}

    items_by_user = {item["user_id"]: item for item in payload["items"]}
    assert items_by_user[11]["reasons"] == ["never_accessed", "incomplete_resources"]
    assert items_by_user[22]["reasons"] == ["incomplete_resources"]
    assert items_by_user[11]["urgency_score"] > items_by_user[22]["urgency_score"]
    assert items_by_user[11]["priority_level"] in {"alta", "critica"}
    assert 33 not in items_by_user


def test_engagement_job_route_runs_and_records_history(app, monkeypatch):
    client = app.test_client()
    fake_client = FakeEngagementClient()
    services = app.extensions["services"]
    monkeypatch.setattr(
        services["connection_service"],
        "build_client",
        lambda payload: fake_client,
    )
    _seed_courses(client, "101")

    def run_inline(job_id, fn, payload):
        fn(job_id, payload)

    services["job_manager"].start_background = run_inline

    response = client.post(
        "/api/engagement/jobs",
        json={
            "base_url": "https://canvas.example.com",
            "access_token": "token",
            "course_refs": ["101"],
            "criteria_mode": "never_accessed_or_incomplete_resources",
            "subject": "Atenção {{student_name}}",
            "message": "Olá {{student_name}}, verifique o curso {{course_name}}.",
            "dry_run": False,
        },
    )

    assert response.status_code == 202
    job_id = response.get_json()["job"]["id"]

    history = client.get("/api/history")
    assert history.status_code == 200
    item = next(entry for entry in history.get_json()["items"] if entry["id"] == job_id)
    assert item["kind"] == "engagement"
    assert item["status"] == "completed"
    assert item["result"]["summary"]["total_matched_students"] == 2
    assert item["result"]["summary"]["total_recipients_sent"] == 2
    assert item["result"]["course_results"][0]["recipients_targeted"] == 2
    assert item["result"]["course_results"][0]["recipients_sent"] == 2
