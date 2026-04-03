from __future__ import annotations


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


def test_group_crud_endpoints(client):
    _seed_courses(client, "101", "202", "303")

    created = client.post(
        "/api/groups",
        json={
            "name": "Grupo Matematica",
            "description": "Turmas do bloco de calculo",
            "course_ids_text": "101\n202",
        },
    )

    assert created.status_code == 201
    item = created.get_json()["item"]
    group_id = item["id"]
    assert item["course_refs"] == ["101", "202"]

    fetched = client.get(f"/api/groups/{group_id}")
    assert fetched.status_code == 200
    assert fetched.get_json()["item"]["name"] == "Grupo Matematica"

    updated = client.put(
        f"/api/groups/{group_id}",
        json={
            "name": "Grupo Matematica Atualizado",
            "description": "Turmas revisadas",
            "course_ids_text": "101\n303",
        },
    )
    assert updated.status_code == 200
    assert updated.get_json()["item"]["course_refs"] == ["101", "303"]

    deleted = client.delete(f"/api/groups/{group_id}")
    assert deleted.status_code == 200
    assert deleted.get_json()["ok"] is True

    listed = client.get("/api/groups")
    assert listed.status_code == 200
    assert listed.get_json()["items"] == []


def test_group_duplicate_name_is_rejected(client):
    _seed_courses(client, "11", "22")

    payload = {
        "name": "Grupo Duplicado",
        "description": "Primeira criacao",
        "course_ids_text": "11\n22",
    }

    first = client.post("/api/groups", json=payload)
    second = client.post("/api/groups", json=payload)

    assert first.status_code == 201
    assert second.status_code == 400
    assert "grupo com esse nome" in second.get_json()["error"].lower()
