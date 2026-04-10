from __future__ import annotations

from src.domain.engagement_service import EngagementService
from src.services.canvas_client import CanvasClient


class FakeEngagementClient:
    def __init__(self):
        self.conversation_id = 9000
        self.conversations_created = []
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
        self.enrollments = {
            "101": [
                {"user_id": 11, "last_activity_at": None, "total_activity_time": 0},
                {"user_id": 22, "last_activity_at": "2026-04-03T02:00:00Z", "total_activity_time": 8 * 60},
                {"user_id": 33, "last_activity_at": "2026-04-03T02:00:00Z", "total_activity_time": 45 * 60},
            ]
        }
        self.assignments = {
            "101": [
                {"id": 99137, "name": "Assign principal", "published": True, "submission_types": ["online_upload"], "points_possible": 10, "grading_type": "points"},
                {"id": 99138, "name": "Quiz vindo por assignments", "published": True, "submission_types": ["online_quiz"], "quiz_id": 79499},
                {"id": 99139, "name": "Assign rascunho", "published": False, "submission_types": ["online_upload"]},
                {"id": 99140, "name": "Assign sem entrega", "published": True, "submission_types": ["none"], "points_possible": 10, "grading_type": "points"},
                {"id": 99141, "name": "Assign no papel", "published": True, "submission_types": ["on_paper"], "points_possible": 10, "grading_type": "points"},
                {"id": 99142, "name": "Assign sem nota", "published": True, "submission_types": ["online_upload"], "points_possible": 10, "grading_type": "not_graded"},
                {"id": 99143, "name": "Assign zero ponto", "published": True, "submission_types": ["online_upload"], "points_possible": 0, "grading_type": "points"},
            ]
        }
        self.quizzes = {
            "101": [
                {"id": 79410, "title": "Quiz 1", "published": True, "quiz_type": "assignment", "points_possible": 5},
                {"id": 79411, "title": "Quiz 2", "published": True, "quiz_type": "assignment", "points_possible": 5},
                {"id": 79412, "title": "Quiz 3", "published": True, "quiz_type": "assignment", "points_possible": 5},
                {"id": 79413, "title": "Quiz 4", "published": True, "quiz_type": "assignment", "points_possible": 5},
                {"id": 79414, "title": "Quiz treino", "published": True, "quiz_type": "practice_quiz", "points_possible": 5},
                {"id": 79415, "title": "Quiz pesquisa", "published": True, "quiz_type": "survey", "points_possible": 5},
            ]
        }
        self.assignment_submissions = {
            "101": {
                "99137": [
                    {"user_id": 11, "workflow_state": "unsubmitted", "submitted_at": None},
                    {"user_id": 22, "workflow_state": "submitted", "submitted_at": "2026-04-03T02:00:00Z"},
                ]
            }
        }
        self.quiz_submissions = {
            "101": {
                "79410": [
                    {"user_id": 11, "workflow_state": "untaken", "finished_at": None},
                    {"user_id": 22, "workflow_state": "complete", "finished_at": "2026-04-03T02:00:00Z"},
                    {"user_id": 33, "workflow_state": "complete", "finished_at": "2026-04-03T02:00:00Z"},
                ],
                "79411": [
                    {"user_id": 22, "workflow_state": "complete", "finished_at": "2026-04-03T02:00:00Z"},
                    {"user_id": 33, "workflow_state": "complete", "finished_at": "2026-04-03T02:00:00Z"},
                ],
                "79412": [
                    {"user_id": 22, "workflow_state": "complete", "finished_at": "2026-04-03T02:00:00Z"},
                    {"user_id": 33, "workflow_state": "complete", "finished_at": "2026-04-03T02:00:00Z"},
                ],
                "79413": [
                    {"user_id": 22, "workflow_state": "complete", "finished_at": "2026-04-03T02:00:00Z"},
                    {"user_id": 33, "workflow_state": "untaken", "finished_at": None},
                ],
                "79414": [],
                "79415": [],
            }
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

    def create_conversation(self, *, recipients, subject, body, context_code=None, force_new=True, group_conversation=False, mode=None, extra_params=None):
        self.conversation_id += 1
        self.conversations_created.append({"recipients": recipients, "subject": subject, "body": body, "context_code": context_code})
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


def test_engagement_preview_combines_selected_filters_and_message_groups(app, monkeypatch):
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
            "criteria_modes": ["never_accessed", "low_total_activity", "missing_quiz", "missing_assignment"],
            "criteria_config": {"max_total_activity_minutes": 10},
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["total_courses"] == 1
    assert payload["summary"]["total_students_found"] == 3
    assert payload["summary"]["total_unique_students_matched"] == 3
    assert payload["summary"]["total_target_messages"] == 4
    assert payload["summary"]["total_inactivity_messages"] == 2
    assert payload["summary"]["total_activity_messages"] == 2
    assert payload["summary"]["total_never_accessed_matches"] == 1
    assert payload["summary"]["total_low_activity_matches"] == 2
    assert payload["summary"]["total_missing_assignment_matches"] == 2
    assert payload["summary"]["total_missing_quiz_matches"] == 2
    assert payload["summary"]["total_activities_checked"] == 5
    assert payload["summary"]["top_priority_course_name"] == "Curso 101"
    assert payload["analysis"]["summary"]["total_unique_students"] == 3
    assert payload["analysis"]["summary"]["clear_unique_students"] == 0
    assert payload["analysis"]["summary"]["missing_quiz_unique_students"] == 2
    assert payload["analysis"]["summary"]["missing_assignment_unique_students"] == 2
    assert payload["courses"][0]["matched_students"] == 3
    assert payload["courses"][0]["target_messages"] == 4
    assert payload["courses"][0]["activity_count"] == 5
    assert payload["courses"][0]["priority_level"] in {"alta", "critica"}
    assert payload["analysis"]["course_rows"][0]["objective_done_pct"] == 33.33
    assert payload["analysis"]["course_rows"][0]["integrated_done_pct"] == 33.33
    student_rows = {row["user_id"]: row for row in payload["analysis"]["student_rows"]}
    assert student_rows[11]["course_names"] == ["Curso 101"]
    assert student_rows[11]["missing_assignment_names"] == ["Assign principal"]
    assert student_rows[33]["missing_quiz_names"] == ["Quiz 4"]

    items_by_key = {(item["user_id"], item["message_kind"]): item for item in payload["items"]}
    assert set(items_by_key) == {
        (11, "inactivity"),
        (11, "missing_activity"),
        (22, "inactivity"),
        (33, "missing_activity"),
    }
    assert items_by_key[(11, "inactivity")]["reasons"] == ["never_accessed", "low_total_activity"]
    assert items_by_key[(11, "missing_activity")]["activity_type"] == "mixed"
    assert "Assign principal" in items_by_key[(11, "missing_activity")]["missing_activity_names"]
    assert "Assign sem entrega" not in items_by_key[(11, "missing_activity")]["missing_activity_names"]
    assert "Quiz treino" not in items_by_key[(11, "missing_activity")]["missing_activity_names"]
    assert items_by_key[(33, "missing_activity")]["missing_quiz_names"] == ["Quiz 4"]


def test_engagement_preview_filters_missing_quizzes_automatically(app, monkeypatch):
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
            "criteria_modes": ["missing_quiz"],
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["total_unique_students_matched"] == 2
    assert payload["summary"]["total_target_messages"] == 2
    assert payload["summary"]["total_missing_quiz_matches"] == 2
    assert payload["summary"]["total_missing_assignment_matches"] == 0
    assert payload["summary"]["total_activities_checked"] == 4
    assert {item["user_id"] for item in payload["items"]} == {11, 33}
    items_by_user = {item["user_id"]: item for item in payload["items"]}
    assert items_by_user[11]["activity_missing_count"] == 4
    assert items_by_user[33]["activity_submitted_count"] == 3
    assert items_by_user[33]["missing_activity_names"] == ["Quiz 4"]


def test_engagement_preview_can_create_csv_report_for_manual_review(app, monkeypatch):
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
            "criteria_modes": ["missing_quiz", "missing_assignment"],
            "save_report": True,
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    report_job = payload["report_job"]
    assert report_job["kind"] == "engagement"
    assert report_job["title"] == "Previa de inativos"
    assert report_job["status"] == "completed"
    assert report_job["result"]["summary"]["preview_only"] is True
    assert report_job["result"]["summary"]["dry_run"] is True
    assert report_job["result"]["course_results"][0]["strategy_used"] == "preview_only"
    assert report_job["result"]["course_results"][0]["recipients_sent"] == 0
    assert report_job["result"]["analysis"]["summary"]["total_unique_students"] == 3
    assert report_job["report_filename"].startswith("engagement-preview-report-")

    csv_response = client.get(f"/api/history/{report_job['id']}/csv")
    assert csv_response.status_code == 200
    csv_text = csv_response.data.decode("utf-8-sig")
    assert "Aluno Zero" in csv_text
    assert "Assign principal" in csv_text
    assert "Curso 101" in csv_text
    assert "Quiz treino" not in csv_text


def test_engagement_preview_accepts_legacy_activity_filter_as_missing_assignment(app, monkeypatch):
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
            "criteria_mode": "missing_activity",
            "criteria_config": {"activity_url": "https://unifil.instructure.com/courses/101/quizzes/79410"},
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["summary"]["criteria_mode"] == "missing_assignment"
    assert payload["summary"]["total_missing_activity_matches"] == 2
    assert {item["user_id"] for item in payload["items"]} == {11, 33}
    assert {item["message_kind"] for item in payload["items"]} == {"missing_activity"}


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
            "criteria_modes": ["never_accessed", "low_total_activity", "missing_quiz", "missing_assignment"],
            "criteria_config": {"max_total_activity_minutes": 10},
            "inactivity_subject": "Acesso {{student_name}}",
            "inactivity_message": "Olá {{student_name}}, vimos {{reason}} em {{course_name}}.",
            "activity_subject": "Pendencia {{student_name}}",
            "activity_message": "Olá {{student_name}}, faltou {{missing_activities}} em {{course_name}}.",
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
    assert item["result"]["summary"]["total_unique_students_matched"] == 3
    assert item["result"]["summary"]["total_target_messages"] == 4
    assert item["result"]["summary"]["total_recipients_sent"] == 4
    assert item["result"]["course_results"][0]["recipients_targeted"] == 4
    assert item["result"]["course_results"][0]["recipients_sent"] == 4
    assert [entry["subject"] for entry in fake_client.conversations_created].count("Acesso Aluno Zero") == 1
    assert [entry["subject"] for entry in fake_client.conversations_created].count("Pendencia Aluno Zero") == 1
    assert any("Quiz 4" in entry["body"] for entry in fake_client.conversations_created)


def test_canvas_client_requests_quiz_submissions_with_associated_submission(monkeypatch):
    client = CanvasClient(
        base_url="https://canvas.example.com",
        access_token="token",
        timeout=5,
        retry_max_attempts=1,
        retry_base_delay=0,
    )
    captured = {}

    def fake_iter(path, *, key, params=None):
        captured["path"] = path
        captured["key"] = key
        captured["params"] = params
        return []

    monkeypatch.setattr(client, "_iter_paginated_payload_key", fake_iter)

    assert client.list_quiz_submissions("101", 79410) == []
    assert captured["path"] == "/api/v1/courses/101/quizzes/79410/submissions"
    assert captured["key"] == "quiz_submissions"
    assert ("include[]", "submission") in captured["params"]


def test_assignment_submission_done_accepts_ungraded_turn_in_content():
    assert EngagementService._assignment_submission_done(
        {"workflow_state": "submitted", "submitted_at": None, "attachments": []}
    )
    assert EngagementService._assignment_submission_done(
        {"workflow_state": "unsubmitted", "submitted_at": None, "attachments": [{"id": 123}]}
    )
    assert EngagementService._assignment_submission_done(
        {"workflow_state": "unsubmitted", "submitted_at": None, "url": "https://example.com/trabalho"}
    )
    assert not EngagementService._assignment_submission_done(
        {"workflow_state": "unsubmitted", "submitted_at": None, "attachments": []}
    )
