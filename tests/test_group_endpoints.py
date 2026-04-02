from __future__ import annotations


def test_group_crud_endpoints(client):
    created = client.post(
        "/api/groups",
        json={
            "name": "Grupo Matemática",
            "description": "Turmas do bloco de cálculo",
            "course_ids_text": "101\n202",
        },
    )

    assert created.status_code == 201
    item = created.get_json()["item"]
    group_id = item["id"]
    assert item["course_refs"] == ["101", "202"]

    fetched = client.get(f"/api/groups/{group_id}")
    assert fetched.status_code == 200
    assert fetched.get_json()["item"]["name"] == "Grupo Matemática"

    updated = client.put(
        f"/api/groups/{group_id}",
        json={
            "name": "Grupo Matemática Atualizado",
            "description": "Turmas revisadas",
            "course_ids_text": "101\n303",
        },
    )
    assert updated.status_code == 200
    assert updated.get_json()["item"]["course_refs"] == ["101", "303"]

    deleted = client.delete(f"/api/groups/{group_id}")
    assert deleted.status_code == 200
    assert deleted.get_json()["ok"] is True


def test_group_duplicate_name_is_rejected(client):
    payload = {
        "name": "Grupo Duplicado",
        "description": "Primeira criação",
        "course_ids_text": "11\n22",
    }

    first = client.post("/api/groups", json=payload)
    second = client.post("/api/groups", json=payload)

    assert first.status_code == 201
    assert second.status_code == 400
    assert "grupo com esse nome" in second.get_json()["error"].lower()
