from __future__ import annotations

from datetime import UTC, datetime, timedelta


class FakeCanvasClient:
    def __init__(self):
        self.current_user = {"id": 55, "name": "Operador"}
        self.courses = {
            "101": {"id": 101, "name": "Calculo I", "course_code": "MAT101", "term": {"name": "2026/1"}},
            "202": {"id": 202, "name": "Fisica I", "course_code": "FIS202", "term": {"name": "2026/1"}},
        }
        self.students = {
            "101": [
                {"id": 1, "name": "Aluno 1"},
                {"id": 2, "name": "Aluno 2"},
            ],
            "202": [
                {"id": 3, "name": "Aluno 3"},
            ],
        }
        self.analytics = {
            "101": [
                {"id": 1, "page_views": 0, "participations": 0},
                {"id": 2, "page_views": 5, "participations": 1},
            ],
            "202": [
                {"id": 3, "page_views": 2, "participations": 0},
            ],
        }
        self.progress = {
            "101": [
                {"id": 1, "progress": {"requirement_count": 2, "requirement_completed_count": 0}},
                {"id": 2, "progress": {"requirement_count": 2, "requirement_completed_count": 2}},
            ],
            "202": [
                {"id": 3, "progress": {"requirement_count": 1, "requirement_completed_count": 1}},
            ],
        }
        now = datetime.now(UTC).replace(microsecond=0)
        self.enrollments = {
            "101": [
                {"user_id": 1, "last_activity_at": None, "total_activity_time": 0},
                {"user_id": 2, "last_activity_at": (now - timedelta(days=2)).isoformat().replace("+00:00", "Z"), "total_activity_time": 3600},
            ],
            "202": [
                {"user_id": 3, "last_activity_at": (now - timedelta(days=20)).isoformat().replace("+00:00", "Z"), "total_activity_time": 300},
            ],
        }
        self.assignments = {
            "101": [{"id": 501, "name": "Assign Calculo", "published": True, "submission_types": ["online_upload"]}],
            "202": [{"id": 502, "name": "Assign Fisica", "published": True, "submission_types": ["online_upload"]}],
        }
        self.quizzes = {
            "101": [
                {"id": 601, "title": "Quiz Calculo 1", "published": True},
                {"id": 602, "title": "Quiz Calculo 2", "published": True},
                {"id": 603, "title": "Quiz Calculo 3", "published": True},
                {"id": 604, "title": "Quiz Calculo 4", "published": True},
            ],
            "202": [
                {"id": 701, "title": "Quiz Fisica 1", "published": True},
                {"id": 702, "title": "Quiz Fisica 2", "published": True},
                {"id": 703, "title": "Quiz Fisica 3", "published": True},
                {"id": 704, "title": "Quiz Fisica 4", "published": True},
            ],
        }
        self.assignment_submissions = {
            "101": {
                "501": [{"user_id": 2, "workflow_state": "submitted", "submitted_at": now.isoformat().replace("+00:00", "Z")}],
            },
            "202": {
                "502": [],
            },
        }
        self.quiz_submissions = {
            "101": {str(quiz_id): [] for quiz_id in [601, 602, 603, 604]},
            "202": {str(quiz_id): [] for quiz_id in [701, 702, 703, 704]},
        }
        self.contexts = {
            101: {"id": "course_101", "name": "Calculo I"},
            202: {"id": "course_202", "name": "Fisica I"},
        }
        self.conversations_created = []
        self.announcements_created = []
        self.deleted_topics = []

    def get_current_user(self):
        return self.current_user

    def get_course(self, course_ref):
        return self.courses[str(course_ref)]

    def list_course_students(self, course_ref):
        return self.students[str(course_ref)]

    def list_course_student_summaries(self, course_ref, student_id=None):
        return self.analytics[str(course_ref)]

    def list_course_student_enrollments(self, course_ref):
        return self.enrollments[str(course_ref)]

    def list_course_assignments(self, course_ref):
        return self.assignments[str(course_ref)]

    def list_course_quizzes(self, course_ref):
        return self.quizzes[str(course_ref)]

    def list_assignment_submissions(self, course_ref, assignment_id):
        return self.assignment_submissions[str(course_ref)][str(assignment_id)]

    def list_quiz_submissions(self, course_ref, quiz_id):
        return self.quiz_submissions[str(course_ref)][str(quiz_id)]

    def find_messageable_context(self, *, course_id, course_name):
        return self.contexts.get(int(course_id))

    def create_conversation(self, **kwargs):
        self.conversations_created.append(kwargs)
        return [{"id": 9000 + len(self.conversations_created)}]

    def create_announcement(self, **kwargs):
        self.announcements_created.append(kwargs)
        topic_id = 7000 + len(self.announcements_created)
        return {
            "id": topic_id,
            "html_url": f"https://canvas.example.com/courses/{kwargs['course_ref']}/discussion_topics/{topic_id}",
            "published": True,
        }

    def delete_discussion_topic(self, *, course_ref, topic_id):
        self.deleted_topics.append({"course_ref": str(course_ref), "topic_id": int(topic_id)})
        return {}


def _connection_payload():
    return {
        "base_url": "https://canvas.example.com",
        "access_token": "token",
        "client_timezone": "America/Sao_Paulo",
    }


def test_announcement_recurrence_preview_and_create(client, app, monkeypatch):
    services = app.extensions["services"]
    fake_client = FakeCanvasClient()
    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: fake_client)

    preview_response = client.post(
        "/api/announcement-recurrences/preview",
        json={
            **_connection_payload(),
            "target_mode": "courses",
            "course_refs": ["101", "202"],
            "title": "Encontro semanal",
            "message_html": "<p>Lembrete</p>",
            "recurrence_type": "weekly",
            "interval_value": 1,
            "first_publish_at_local": "2030-05-01T19:00",
            "occurrence_count": 3,
            "lock_comment": True,
        },
    )
    assert preview_response.status_code == 200
    preview_payload = preview_response.get_json()
    assert preview_payload["summary"]["courses"] == 2
    assert preview_payload["summary"]["occurrences_per_course"] == 3
    assert preview_payload["summary"]["total_announcements"] == 6

    create_response = client.post(
        "/api/announcement-recurrences",
        json={
            **_connection_payload(),
            "target_mode": "courses",
            "course_refs": ["101", "202"],
            "name": "Quinta 19h",
            "title": "Encontro semanal",
            "message_html": "<p>Lembrete</p>",
            "recurrence_type": "weekly",
            "interval_value": 1,
            "first_publish_at_local": "2030-05-01T19:00",
            "occurrence_count": 2,
            "lock_comment": True,
        },
    )
    assert create_response.status_code == 201
    payload = create_response.get_json()
    assert payload["created_count"] == 4
    assert payload["failure_count"] == 0
    assert payload["item"]["name"] == "Quinta 19h"
    assert payload["item"]["total_items"] == 4
    assert len(fake_client.announcements_created) == 4
    assert fake_client.announcements_created[0]["title"] == "Encontro semanal"


def test_announcement_recurrence_renders_course_placeholders(client, app, monkeypatch):
    services = app.extensions["services"]
    fake_client = FakeCanvasClient()
    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: fake_client)

    create_response = client.post(
        "/api/announcement-recurrences",
        json={
            **_connection_payload(),
            "target_mode": "courses",
            "course_refs": ["101"],
            "name": "Base disciplina",
            "title": "Aviso - {{course_name}}",
            "message_html": "<p>{{course_code}} | {{course_ref}} | {{course_name}}</p>",
            "recurrence_type": "weekly",
            "interval_value": 1,
            "first_publish_at_local": "2030-05-01T19:00",
            "occurrence_count": 1,
            "lock_comment": False,
        },
    )

    assert create_response.status_code == 201
    assert fake_client.announcements_created[0]["title"] == "Aviso - Calculo I"
    assert fake_client.announcements_created[0]["message_html"] == "<p>MAT101 | 101 | Calculo I</p>"


def test_announcement_recurrence_cancel_removes_future_topics(client, app, monkeypatch):
    services = app.extensions["services"]
    fake_client = FakeCanvasClient()
    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: fake_client)

    created = client.post(
        "/api/announcement-recurrences",
        json={
            **_connection_payload(),
            "target_mode": "courses",
            "course_refs": ["101"],
            "name": "Mudou o dia",
            "title": "Encontro semanal",
            "message_html": "<p>Lembrete</p>",
            "recurrence_type": "weekly",
            "interval_value": 1,
            "first_publish_at_local": "2030-05-01T19:00",
            "occurrence_count": 2,
            "lock_comment": False,
        },
    ).get_json()["item"]

    cancel_response = client.post(
        f"/api/announcement-recurrences/{created['id']}/cancel",
        json={
            **_connection_payload(),
            "cancel_reason": "Mudanca de agenda",
        },
    )
    assert cancel_response.status_code == 200
    payload = cancel_response.get_json()
    assert payload["canceled_count"] == 2
    assert payload["failure_count"] == 0
    assert len(fake_client.deleted_topics) == 2

    listed = client.get("/api/announcement-recurrences?include_inactive=1")
    assert listed.status_code == 200
    items = listed.get_json()["items"]
    assert items[0]["is_active"] is False
    assert items[0]["canceled_items"] == 2


def test_announcement_recurrence_update_replaces_future_topics(client, app, monkeypatch):
    services = app.extensions["services"]
    fake_client = FakeCanvasClient()
    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: fake_client)

    created = client.post(
        "/api/announcement-recurrences",
        json={
            **_connection_payload(),
            "target_mode": "courses",
            "course_refs": ["101"],
            "name": "Quinta 19h",
            "title": "Encontro semanal",
            "message_html": "<p>Lembrete</p>",
            "recurrence_type": "weekly",
            "interval_value": 1,
            "first_publish_at_local": "2030-05-01T19:00",
            "occurrence_count": 2,
            "lock_comment": True,
        },
    ).get_json()["item"]

    update_response = client.put(
        f"/api/announcement-recurrences/{created['id']}",
        json={
            **_connection_payload(),
            "target_mode": "courses",
            "course_refs": ["101"],
            "name": "Quinta 20h",
            "title": "Encontro atualizado",
            "message_html": "<p>Novo horario</p>",
            "recurrence_type": "daily",
            "interval_value": 1,
            "first_publish_at_local": "2030-05-10T20:00",
            "occurrence_count": 1,
            "lock_comment": False,
        },
    )
    assert update_response.status_code == 200
    payload = update_response.get_json()
    assert payload["replaced_count"] == 2
    assert payload["created_count"] == 1
    assert payload["failure_count"] == 0
    assert payload["item"]["id"] == created["id"]
    assert payload["item"]["name"] == "Quinta 20h"
    assert payload["item"]["title"] == "Encontro atualizado"
    assert payload["item"]["future_items"] == 1
    assert len(fake_client.deleted_topics) == 2
    assert len(fake_client.announcements_created) == 3
    assert fake_client.announcements_created[-1]["title"] == "Encontro atualizado"


def test_announcement_recurrence_preview_shows_course_diff(client, app, monkeypatch):
    services = app.extensions["services"]
    fake_client = FakeCanvasClient()
    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: fake_client)

    created = client.post(
        "/api/announcement-recurrences",
        json={
            **_connection_payload(),
            "target_mode": "courses",
            "course_refs": ["101", "202"],
            "name": "Base semanal",
            "title": "Encontro semanal",
            "message_html": "<p>Lembrete</p>",
            "recurrence_type": "weekly",
            "interval_value": 1,
            "first_publish_at_local": "2030-05-01T19:00",
            "occurrence_count": 2,
            "lock_comment": True,
        },
    ).get_json()["item"]

    preview_response = client.post(
        "/api/announcement-recurrences/preview",
        json={
            **_connection_payload(),
            "recurrence_id": created["id"],
            "target_mode": "courses",
            "course_refs": ["101"],
            "name": "Base semanal",
            "title": "Encontro semanal",
            "message_html": "<p>Lembrete</p>",
            "recurrence_type": "weekly",
            "interval_value": 1,
            "first_publish_at_local": "2030-05-01T19:00",
            "occurrence_count": 2,
            "lock_comment": True,
        },
    )
    assert preview_response.status_code == 200
    payload = preview_response.get_json()
    assert payload["edit_diff"]["removed_courses"] == 1
    assert payload["edit_diff"]["unchanged_courses"] == 1
    assert payload["edit_diff"]["updated_courses"] == 0
    assert payload["edit_diff"]["delete_items_expected"] == 2


def test_announcement_recurrence_update_removes_only_deselected_course(client, app, monkeypatch):
    services = app.extensions["services"]
    fake_client = FakeCanvasClient()
    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: fake_client)

    created = client.post(
        "/api/announcement-recurrences",
        json={
            **_connection_payload(),
            "target_mode": "courses",
            "course_refs": ["101", "202"],
            "name": "Base semanal",
            "title": "Encontro semanal",
            "message_html": "<p>Lembrete</p>",
            "recurrence_type": "weekly",
            "interval_value": 1,
            "first_publish_at_local": "2030-05-01T19:00",
            "occurrence_count": 2,
            "lock_comment": True,
        },
    ).get_json()["item"]

    update_response = client.put(
        f"/api/announcement-recurrences/{created['id']}",
        json={
            **_connection_payload(),
            "target_mode": "courses",
            "course_refs": ["101"],
            "name": "Base semanal",
            "title": "Encontro semanal",
            "message_html": "<p>Lembrete</p>",
            "recurrence_type": "weekly",
            "interval_value": 1,
            "first_publish_at_local": "2030-05-01T19:00",
            "occurrence_count": 2,
            "lock_comment": True,
        },
    )
    assert update_response.status_code == 200
    payload = update_response.get_json()
    assert payload["diff"]["removed_courses"] == 1
    assert payload["diff"]["unchanged_courses"] == 1
    assert payload["created_count"] == 0
    assert payload["failure_count"] == 0
    assert len(fake_client.deleted_topics) == 2
    assert all(item["course_ref"] == "202" for item in fake_client.deleted_topics)
    assert len(fake_client.announcements_created) == 4
    assert payload["item"]["future_items"] == 2


def test_engagement_filters_use_selected_inactivity_and_assignment_lookup(client, app, monkeypatch):
    services = app.extensions["services"]
    fake_client = FakeCanvasClient()
    monkeypatch.setattr(services["connection_service"], "build_client", lambda payload: fake_client)

    response = client.post(
        "/api/engagement/inactive-targets",
        json={
            **_connection_payload(),
            "target_mode": "courses",
            "course_refs": ["101", "202"],
            "criteria_modes": ["low_total_activity", "missing_assignment"],
            "criteria_config": {"max_total_activity_minutes": 10},
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["total_students_found"] == 3
    assert payload["summary"]["total_missing_assignment_matches"] == 2
    assert payload["summary"]["total_low_activity_matches"] == 2
    assert payload["summary"]["total_unique_students_matched"] == 2
    assert payload["summary"]["total_target_messages"] == 4
    assert payload["summary"]["total_activities_checked"] == 2
    assert payload["summary"]["top_priority_course_name"]
    assert payload["courses"][0]["urgency_score"] >= payload["courses"][-1]["urgency_score"]
    matched_names_by_kind = {(item["student_name"], item["message_kind"]) for item in payload["items"]}
    assert ("Aluno 1", "inactivity") in matched_names_by_kind
    assert ("Aluno 1", "missing_activity") in matched_names_by_kind
    assert ("Aluno 3", "inactivity") in matched_names_by_kind
    assert ("Aluno 3", "missing_activity") in matched_names_by_kind
