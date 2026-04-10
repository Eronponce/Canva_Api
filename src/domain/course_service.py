from __future__ import annotations

from src.utils.parsing import parse_course_references


def short_course_code(course_code: str | None) -> str:
    normalized = str(course_code or "").strip()
    if not normalized:
        return ""
    return normalized.split("@", 1)[0].strip() or normalized


class CourseService:
    def __init__(self, connection_service, group_repository, course_repository):
        self.connection_service = connection_service
        self.group_repository = group_repository
        self.course_repository = course_repository

    def resolve_payload_course_refs(self, payload: dict) -> list[str]:
        direct_refs = payload.get("course_refs")
        if isinstance(direct_refs, list) and direct_refs:
            refs = [str(item).strip() for item in direct_refs if str(item).strip()]
            return list(dict.fromkeys(refs))

        course_ids_text = payload.get("course_ids_text", "")
        parsed_refs = parse_course_references(course_ids_text)
        if parsed_refs:
            return parsed_refs

        group_ids = payload.get("group_ids") or []
        select_all_groups = bool(payload.get("select_all_groups"))

        if select_all_groups:
            selected_groups = self.group_repository.list_groups(active_only=True)
        elif isinstance(group_ids, list):
            selected_ids = {str(item).strip() for item in group_ids if str(item).strip()}
            selected_groups = [
                group
                for group in self.group_repository.list_groups(active_only=True)
                if group.get("id") in selected_ids
            ]
        else:
            selected_groups = []

        refs: list[str] = []
        for group in selected_groups:
            refs.extend(group.get("course_refs", []))

        return list(dict.fromkeys(str(ref).strip() for ref in refs if str(ref).strip()))

    def resolve_courses(self, payload: dict) -> dict:
        course_refs = self.resolve_payload_course_refs(payload)
        if not course_refs:
            raise ValueError("Selecione ou informe pelo menos um course_id para carregar os nomes das turmas.")

        client = self.connection_service.build_client(payload)
        resolved = []

        for course_ref in course_refs:
            try:
                course = client.get_course(course_ref)
                context = None
                try:
                    context = client.find_messageable_context(
                        course_id=course["id"],
                        course_name=course.get("name") or str(course["id"]),
                    )
                except Exception:  # noqa: BLE001
                    context = None

                resolved.append(
                    {
                        "course_ref": course_ref,
                        "status": "ok",
                        "course": {
                            "id": course.get("id"),
                            "name": course.get("name"),
                            "course_code": course.get("course_code"),
                            "course_code_short": short_course_code(course.get("course_code")),
                            "workflow_state": course.get("workflow_state"),
                            "term_name": (course.get("term") or {}).get("name"),
                            "messageable_context": bool(context),
                        },
                    }
                )
            except Exception as exc:  # noqa: BLE001
                resolved.append(
                    {
                        "course_ref": course_ref,
                        "status": "error",
                        "error": str(exc),
                    }
                )

        return {
            "items": resolved,
            "success_count": len([item for item in resolved if item["status"] == "ok"]),
            "failure_count": len([item for item in resolved if item["status"] == "error"]),
        }

    def list_catalog(self, payload: dict) -> dict:
        client = self.connection_service.build_client(payload)
        search_term = (payload.get("search_term") or "").strip().lower()
        courses = client.list_accessible_courses()
        registered_refs = {
            item["course_ref"]
            for item in self.course_repository.list_courses(active_only=None)
        }

        filtered = []
        for course in courses:
            course_ref = str(course.get("id", "")).strip()
            haystack = " ".join(
                [
                    course_ref,
                    course.get("name", "") or "",
                    course.get("course_code", "") or "",
                    ((course.get("term") or {}).get("name", "")),
                ]
            ).lower()
            if search_term and search_term not in haystack:
                continue
            filtered.append(
                {
                    "id": course.get("id"),
                    "course_ref": course_ref,
                    "name": course.get("name"),
                    "course_code": course.get("course_code"),
                    "course_code_short": short_course_code(course.get("course_code")),
                    "term_name": (course.get("term") or {}).get("name"),
                    "workflow_state": course.get("workflow_state"),
                    "already_registered": course_ref in registered_refs,
                }
            )

        filtered.sort(key=lambda item: (item.get("name") or "").lower())
        return {
            "items": filtered,
            "total_found": len(filtered),
        }

    def list_registered_courses(self, *, include_inactive: bool = False) -> dict:
        items = self.course_repository.list_courses(active_only=None if include_inactive else True)
        return {"items": items}

    def add_registered_course(self, payload: dict) -> dict:
        client = self.connection_service.build_client(payload)
        course_ref = str(payload.get("course_ref", "")).strip()
        if not course_ref:
            raise ValueError("Informe o numero do curso para cadastrar.")

        course = client.get_course(course_ref)
        item = self.course_repository.upsert_course(self._course_payload(course_ref, course))
        return {"item": item}

    def add_registered_courses(self, payload: dict) -> dict:
        client = self.connection_service.build_client(payload)
        course_refs = [
            str(item).strip()
            for item in (payload.get("course_refs") or [])
            if str(item).strip()
        ]
        course_refs = list(dict.fromkeys(course_refs))
        if not course_refs:
            raise ValueError("Selecione pelo menos um curso para cadastrar.")

        items = []
        created_count = 0
        updated_count = 0

        for course_ref in course_refs:
            existing = self.course_repository.get_course_by_ref(course_ref, active_only=None)
            course = client.get_course(course_ref)
            item = self.course_repository.upsert_course(self._course_payload(course_ref, course))
            items.append(item)
            if existing:
                updated_count += 1
            else:
                created_count += 1

        return {
            "items": items,
            "created_count": created_count,
            "updated_count": updated_count,
        }

    def delete_registered_course(self, course_ref: str) -> dict:
        removed = self.course_repository.delete_course(course_ref)
        if not removed:
            raise ValueError("Curso cadastrado nao encontrado.")
        return {"ok": True}

    def reactivate_registered_course(self, course_ref: str) -> dict:
        item = self.course_repository.reactivate_course(course_ref)
        if not item:
            raise ValueError("Curso cadastrado nao encontrado.")
        return {"item": item}

    def list_groups(self, *, include_inactive: bool = False) -> dict:
        items = self.group_repository.list_groups(active_only=None if include_inactive else True)
        return {"items": items}

    def get_group(self, group_id: str, *, include_inactive: bool = False) -> dict:
        group = self.group_repository.get_group(group_id, active_only=None if include_inactive else True)
        if not group:
            raise ValueError("Grupo nao encontrado.")
        return {"item": group}

    def create_group(self, payload: dict) -> dict:
        course_refs = self.resolve_payload_course_refs(payload)
        saved = self.group_repository.create_group(
            payload.get("name", ""),
            course_refs,
            payload.get("description", ""),
            payload.get("notes", ""),
        )
        return {"item": saved}

    def update_group(self, group_id: str, payload: dict) -> dict:
        course_refs = self.resolve_payload_course_refs(payload)
        saved = self.group_repository.update_group(
            group_id,
            payload.get("name", ""),
            course_refs,
            payload.get("description", ""),
            payload.get("notes", ""),
        )
        return {"item": saved}

    def delete_group(self, group_id: str) -> dict:
        deleted = self.group_repository.delete_group(group_id)
        if not deleted:
            raise ValueError("Grupo nao encontrado.")
        return {"ok": True}

    def reactivate_group(self, group_id: str) -> dict:
        item = self.group_repository.reactivate_group(group_id)
        if not item:
            raise ValueError("Grupo nao encontrado.")
        return {"item": item}

    @staticmethod
    def _course_payload(course_ref: str, course: dict) -> dict:
        return {
            "course_ref": course_ref,
            "canvas_course_id": course.get("id"),
            "course_name": course.get("name"),
            "course_code": course.get("course_code"),
            "term_name": (course.get("term") or {}).get("name"),
            "workflow_state": course.get("workflow_state"),
            "source_type": "canvas_lookup",
            "metadata_json": {
                "enrollment_term_id": course.get("enrollment_term_id"),
                "workflow_state": course.get("workflow_state"),
            },
        }
