from __future__ import annotations

from uuid import uuid4

from src.storage.json_store import JsonFileStore
from src.utils.time_utils import utc_now_iso


class GroupStore:
    def __init__(self, groups_file):
        self.store = JsonFileStore(groups_file, list)

    def list_groups(self) -> list[dict]:
        groups = self.store.read() or []
        return sorted(
            groups,
            key=lambda item: (
                item.get("name", "").lower(),
                item.get("updated_at", ""),
            ),
        )

    def get_group(self, group_id: str) -> dict | None:
        return next((group for group in self.list_groups() if group.get("id") == group_id), None)

    def create_group(self, name: str, course_refs: list[str], description: str = "") -> dict:
        cleaned_name = name.strip()
        cleaned_description = description.strip()
        if not cleaned_name:
            raise ValueError("Informe um nome para o grupo de turmas.")
        if not course_refs:
            raise ValueError("Informe ao menos uma turma para salvar o grupo.")

        if any(group.get("name", "").lower() == cleaned_name.lower() for group in self.list_groups()):
            raise ValueError("Ja existe um grupo com esse nome. Use editar para atualizar.")

        saved_at = utc_now_iso()
        payload = {
            "id": uuid4().hex[:12],
            "name": cleaned_name,
            "description": cleaned_description,
            "course_refs": course_refs,
            "updated_at": saved_at,
            "created_at": saved_at,
        }

        def updater(groups):
            groups.append(payload)
            return groups

        self.store.update(updater)
        return payload

    def update_group(self, group_id: str, name: str, course_refs: list[str], description: str = "") -> dict:
        cleaned_name = name.strip()
        cleaned_description = description.strip()
        if not cleaned_name:
            raise ValueError("Informe um nome para o grupo de turmas.")
        if not course_refs:
            raise ValueError("Informe ao menos uma turma para salvar o grupo.")

        existing_group = self.get_group(group_id)
        if not existing_group:
            raise ValueError("Grupo nao encontrado.")

        for group in self.list_groups():
            if group.get("id") == group_id:
                continue
            if group.get("name", "").lower() == cleaned_name.lower():
                raise ValueError("Ja existe outro grupo com esse nome.")

        payload = {
            "id": group_id,
            "name": cleaned_name,
            "description": cleaned_description,
            "course_refs": course_refs,
            "updated_at": utc_now_iso(),
            "created_at": existing_group.get("created_at", utc_now_iso()),
        }

        def updater(groups):
            filtered = [item for item in groups if item.get("id") != group_id]
            filtered.append(payload)
            return filtered

        self.store.update(updater)
        return payload

    def delete_group(self, group_id: str) -> bool:
        removed = False

        def updater(groups):
            nonlocal removed
            filtered = [item for item in groups if item.get("id") != group_id]
            removed = len(filtered) != len(groups)
            return filtered

        self.store.update(updater)
        return removed
