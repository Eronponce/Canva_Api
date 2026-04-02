from __future__ import annotations

from src.storage.group_store import GroupStore
from src.storage.registered_course_store import RegisteredCourseStore
from src.utils.parsing import parse_course_references


class CourseService:
    def __init__(
        self,
        connection_service,
        group_store: GroupStore,
        registered_course_store: RegisteredCourseStore,
    ):
        self.connection_service = connection_service
        self.group_store = group_store
        self.registered_course_store = registered_course_store

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

        selected_groups = []
        if select_all_groups:
            selected_groups = self.group_store.list_groups()
        elif isinstance(group_ids, list):
            selected_ids = {str(item) for item in group_ids}
            selected_groups = [
                group
                for group in self.group_store.list_groups()
                if group.get("id") in selected_ids
            ]

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

        filtered = []
        for course in courses:
            haystack = " ".join(
                [
                    str(course.get("id", "")),
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
                    "name": course.get("name"),
                    "course_code": course.get("course_code"),
                    "term_name": (course.get("term") or {}).get("name"),
                    "workflow_state": course.get("workflow_state"),
                }
            )

        filtered.sort(key=lambda item: (item.get("name") or "").lower())
        return {
            "items": filtered[:250],
            "total_found": len(filtered),
        }

    def list_registered_courses(self) -> dict:
        items = self.registered_course_store.list_courses()
        return {"items": items}

    def add_registered_course(self, payload: dict) -> dict:
        client = self.connection_service.build_client(payload)
        course_ref = str(payload.get("course_ref", "")).strip()
        if not course_ref:
            raise ValueError("Informe o numero do curso para cadastrar.")

        course = client.get_course(course_ref)
        item = self.registered_course_store.add_course(
            {
                "course_ref": course_ref,
                "canvas_course_id": course.get("id"),
                "course_name": course.get("name"),
                "course_code": course.get("course_code"),
                "term_name": (course.get("term") or {}).get("name"),
                "workflow_state": course.get("workflow_state"),
            }
        )
        return {"item": item}

    def delete_registered_course(self, course_ref: str) -> dict:
        removed = self.registered_course_store.delete_course(course_ref)
        if not removed:
            raise ValueError("Curso cadastrado nao encontrado.")
        return {"ok": True}

    def list_groups(self) -> dict:
        items = [self._attach_course_details(group) for group in self.group_store.list_groups()]
        return {"items": items}

    def get_group(self, group_id: str) -> dict:
        group = self.group_store.get_group(group_id)
        if not group:
            raise ValueError("Grupo nao encontrado.")
        return {"item": self._attach_course_details(group)}

    def create_group(self, payload: dict) -> dict:
        course_refs = self.resolve_payload_course_refs(payload)
        saved = self.group_store.create_group(
            payload.get("name", ""),
            course_refs,
            payload.get("description", ""),
        )
        return {"item": self._attach_course_details(saved)}

    def update_group(self, group_id: str, payload: dict) -> dict:
        course_refs = self.resolve_payload_course_refs(payload)
        saved = self.group_store.update_group(
            group_id,
            payload.get("name", ""),
            course_refs,
            payload.get("description", ""),
        )
        return {"item": self._attach_course_details(saved)}

    def delete_group(self, group_id: str) -> dict:
        deleted = self.group_store.delete_group(group_id)
        if not deleted:
            raise ValueError("Grupo nao encontrado.")
        return {"ok": True}

    def _course_lookup(self) -> dict[str, dict]:
        return {
            str(item.get("course_ref")): item
            for item in self.registered_course_store.list_courses()
        }

    def _attach_course_details(self, group: dict) -> dict:
        lookup = self._course_lookup()
        enriched = dict(group)
        enriched["courses"] = [
            {
                "course_ref": course_ref,
                "course_name": (lookup.get(str(course_ref)) or {}).get("course_name", ""),
                "course_code": (lookup.get(str(course_ref)) or {}).get("course_code", ""),
                "term_name": (lookup.get(str(course_ref)) or {}).get("term_name", ""),
                "canvas_course_id": (lookup.get(str(course_ref)) or {}).get("canvas_course_id"),
            }
            for course_ref in group.get("course_refs", [])
        ]
        return enriched
