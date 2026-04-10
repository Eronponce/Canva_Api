from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import quote

import requests

from src.utils.parsing import bool_to_canvas


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class CanvasApiError(Exception):
    message: str
    status_code: int | None = None
    details: dict | list | str | None = None

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
        }


class CanvasClient:
    def __init__(
        self,
        *,
        base_url: str,
        access_token: str,
        timeout: int,
        retry_max_attempts: int,
        retry_base_delay: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retry_max_attempts = retry_max_attempts
        self.retry_base_delay = retry_base_delay
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            }
        )

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = f"/{path}"
        return f"{self.base_url}{path}"

    def _extract_json_or_text(self, response: requests.Response):
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                return response.json()
            except ValueError:
                return response.text
        return response.text

    def _request(
        self,
        method: str,
        path: str,
        *,
        params=None,
        data=None,
        files=None,
        headers=None,
        use_auth: bool = True,
        allow_redirects: bool = True,
        expected_status: Iterable[int] = (200,),
    ) -> tuple[object, requests.Response]:
        url = self._build_url(path)
        expected_status = set(expected_status)
        request_callable = self.session.request if use_auth else requests.request

        for attempt in range(1, self.retry_max_attempts + 1):
            response = request_callable(
                method=method,
                url=url,
                params=params,
                data=data,
                files=files,
                headers=headers,
                timeout=self.timeout,
                allow_redirects=allow_redirects,
            )

            if response.status_code in expected_status:
                return self._extract_json_or_text(response), response

            should_retry = response.status_code == 429 or 500 <= response.status_code < 600
            if should_retry and attempt < self.retry_max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else self.retry_base_delay * (2 ** (attempt - 1))
                LOGGER.warning(
                    "Canvas request retrying | status=%s attempt=%s/%s delay=%.2fs url=%s",
                    response.status_code,
                    attempt,
                    self.retry_max_attempts,
                    delay,
                    url,
                )
                time.sleep(delay)
                continue

            details = self._extract_json_or_text(response)
            raise CanvasApiError(
                message=f"Canvas respondeu com status {response.status_code} para {method.upper()} {url}",
                status_code=response.status_code,
                details=details,
            )

        raise CanvasApiError(message=f"Falha inesperada ao acessar {url}.")

    def _iter_paginated(self, path: str, *, params=None) -> list[dict]:
        current_url = self._build_url(path)
        current_params = params
        items: list[dict] = []

        while current_url:
            payload, response = self._request(
                "GET",
                current_url,
                params=current_params,
                expected_status=(200,),
            )
            current_params = None

            if isinstance(payload, list):
                items.extend(payload)
            else:
                raise CanvasApiError(
                    message="Resposta paginada do Canvas não retornou uma lista.",
                    details=payload,
                )

            current_url = self._next_link(response.headers.get("Link", ""))

        return items

    def _iter_paginated_payload_key(self, path: str, *, key: str, params=None) -> list[dict]:
        current_url = self._build_url(path)
        current_params = params
        items: list[dict] = []

        while current_url:
            payload, response = self._request(
                "GET",
                current_url,
                params=current_params,
                expected_status=(200,),
            )
            current_params = None

            if isinstance(payload, dict) and isinstance(payload.get(key), list):
                items.extend(payload[key])
            elif isinstance(payload, list):
                items.extend(payload)
            else:
                raise CanvasApiError(
                    message=f"Resposta paginada do Canvas nao retornou uma lista em {key}.",
                    details=payload,
                )

            current_url = self._next_link(response.headers.get("Link", ""))

        return items

    @staticmethod
    def _next_link(link_header: str) -> str | None:
        for part in link_header.split(","):
            section = part.strip()
            if 'rel="next"' not in section:
                continue
            start = section.find("<")
            end = section.find(">")
            if start != -1 and end != -1:
                return section[start + 1 : end]
        return None

    def get_current_user(self) -> dict:
        payload, _ = self._request("GET", "/api/v1/users/self", expected_status=(200,))
        return payload

    def list_accessible_courses(self) -> list[dict]:
        params = [("per_page", "100"), ("include[]", "term")]
        return self._iter_paginated("/api/v1/courses", params=params)

    def get_course(self, course_ref: str) -> dict:
        safe_ref = quote(str(course_ref), safe=":")
        payload, _ = self._request(
            "GET",
            f"/api/v1/courses/{safe_ref}",
            params=[("include[]", "term")],
            expected_status=(200,),
        )
        return payload

    def list_course_students(self, course_ref: str) -> list[dict]:
        safe_ref = quote(str(course_ref), safe=":")
        params = [
            ("per_page", "100"),
            ("enrollment_type[]", "student"),
            ("enrollment_state[]", "active"),
            ("include[]", "uuid"),
        ]
        return self._iter_paginated(f"/api/v1/courses/{safe_ref}/users", params=params)

    def list_course_student_enrollments(self, course_ref: str) -> list[dict]:
        safe_ref = quote(str(course_ref), safe=":")
        params = [
            ("per_page", "100"),
            ("type[]", "StudentEnrollment"),
            ("state[]", "active"),
            ("include[]", "user"),
        ]
        return self._iter_paginated(f"/api/v1/courses/{safe_ref}/enrollments", params=params)

    def list_course_student_summaries(self, course_ref: str, *, student_id: int | None = None) -> list[dict]:
        safe_ref = quote(str(course_ref), safe=":")
        params: list[tuple[str, str]] = [("per_page", "100"), ("sort_column", "name")]
        if student_id is not None:
            params.append(("student_id", str(student_id)))
        return self._iter_paginated(f"/api/v1/courses/{safe_ref}/analytics/student_summaries", params=params)

    def list_course_assignments(self, course_ref: str) -> list[dict]:
        safe_ref = quote(str(course_ref), safe=":")
        params = [("per_page", "100"), ("order_by", "position")]
        return self._iter_paginated(f"/api/v1/courses/{safe_ref}/assignments", params=params)

    def list_course_quizzes(self, course_ref: str) -> list[dict]:
        safe_ref = quote(str(course_ref), safe=":")
        params = [("per_page", "100")]
        return self._iter_paginated(f"/api/v1/courses/{safe_ref}/quizzes", params=params)

    def list_assignment_submissions(self, course_ref: str, assignment_id: int | str) -> list[dict]:
        safe_ref = quote(str(course_ref), safe=":")
        safe_assignment_id = quote(str(assignment_id), safe=":")
        params = [("per_page", "100")]
        return self._iter_paginated(
            f"/api/v1/courses/{safe_ref}/assignments/{safe_assignment_id}/submissions",
            params=params,
        )

    def list_quiz_submissions(self, course_ref: str, quiz_id: int | str) -> list[dict]:
        safe_ref = quote(str(course_ref), safe=":")
        safe_quiz_id = quote(str(quiz_id), safe=":")
        params = [("per_page", "100"), ("include[]", "submission")]
        return self._iter_paginated_payload_key(
            f"/api/v1/courses/{safe_ref}/quizzes/{safe_quiz_id}/submissions",
            key="quiz_submissions",
            params=params,
        )

    def create_announcement(
        self,
        *,
        course_ref: str,
        title: str,
        message_html: str,
        published: bool,
        delayed_post_at: str | None,
        lock_comment: bool,
        attachment: dict | None = None,
    ) -> dict:
        safe_ref = quote(str(course_ref), safe=":")
        form_data = [
            ("title", title),
            ("message", message_html),
            ("is_announcement", "true"),
            ("published", bool_to_canvas(published)),
            ("lock_comment", bool_to_canvas(lock_comment)),
        ]

        if delayed_post_at:
            form_data.append(("delayed_post_at", delayed_post_at))

        if attachment:
            with Path(str(attachment["temp_path"])).open("rb") as file_handle:
                payload, _ = self._request(
                    "POST",
                    f"/api/v1/courses/{safe_ref}/discussion_topics",
                    data=form_data,
                    files={
                        "attachment": (
                            attachment["original_name"],
                            file_handle,
                            attachment.get("content_type") or "application/octet-stream",
                        )
                    },
                    expected_status=(200, 201),
                )
        else:
            payload, _ = self._request(
                "POST",
                f"/api/v1/courses/{safe_ref}/discussion_topics",
                data=form_data,
                expected_status=(200, 201),
            )
        return payload

    def delete_discussion_topic(self, *, course_ref: str, topic_id: int | str) -> dict | str:
        safe_ref = quote(str(course_ref), safe=":")
        safe_topic_id = quote(str(topic_id), safe=":")
        payload, _ = self._request(
            "DELETE",
            f"/api/v1/courses/{safe_ref}/discussion_topics/{safe_topic_id}",
            expected_status=(200, 204),
        )
        return payload

    def update_announcement(
        self,
        *,
        course_ref: str,
        topic_id: int | str,
        title: str,
        message_html: str,
        lock_comment: bool | None = None,
    ) -> dict:
        safe_ref = quote(str(course_ref), safe=":")
        safe_topic_id = quote(str(topic_id), safe=":")
        form_data = [
            ("title", title),
            ("message", message_html),
        ]

        if lock_comment is not None:
            form_data.append(("lock_comment", bool_to_canvas(lock_comment)))

        payload, _ = self._request(
            "PUT",
            f"/api/v1/courses/{safe_ref}/discussion_topics/{safe_topic_id}",
            data=form_data,
            expected_status=(200,),
        )
        return payload

    def search_recipients(
        self,
        *,
        search: str | None = None,
        context: str | None = None,
        recipient_type: str | None = None,
        user_id: int | None = None,
        permissions: list[str] | None = None,
    ) -> list[dict]:
        params: list[tuple[str, str]] = [("per_page", "100")]

        if search is not None:
            params.append(("search", search))
        if context:
            params.append(("context", context))
        if recipient_type:
            params.append(("type", recipient_type))
        if user_id is not None:
            params.append(("user_id", str(user_id)))
        for permission in permissions or []:
            params.append(("permissions[]", permission))

        return self._iter_paginated("/api/v1/search/recipients", params=params)

    def find_messageable_context(self, *, course_id: int, course_name: str) -> dict | None:
        results = self.search_recipients(
            search=course_name,
            recipient_type="context",
            permissions=["send_messages"],
        )
        for item in results:
            if str(item.get("id")) == f"course_{course_id}":
                return item
        return None

    def create_conversation(
        self,
        *,
        recipients: list[str | int],
        subject: str,
        body: str,
        context_code: str | None = None,
        force_new: bool = True,
        group_conversation: bool = False,
        mode: str | None = None,
        attachment_ids: list[int] | None = None,
        extra_params: dict[str, str | bool | int] | None = None,
    ):
        form_data: list[tuple[str, str]] = []
        for recipient in recipients:
            form_data.append(("recipients[]", str(recipient)))

        form_data.extend(
            [
                ("subject", subject),
                ("body", body),
                ("force_new", bool_to_canvas(force_new)),
                ("group_conversation", bool_to_canvas(group_conversation)),
            ]
        )

        if context_code:
            form_data.append(("context_code", context_code))
        if mode:
            form_data.append(("mode", mode))
        for attachment_id in attachment_ids or []:
            form_data.append(("attachment_ids[]", str(attachment_id)))
        for key, value in (extra_params or {}).items():
            if isinstance(value, bool):
                form_data.append((key, bool_to_canvas(value)))
            else:
                form_data.append((key, str(value)))

        payload, _ = self._request(
            "POST",
            "/api/v1/conversations",
            data=form_data,
            expected_status=(200, 201),
        )
        return payload

    def initiate_user_file_upload(
        self,
        *,
        filename: str,
        size: int,
        content_type: str,
        parent_folder_path: str = "conversation attachments",
        on_duplicate: str = "rename",
    ) -> dict:
        payload, _ = self._request(
            "POST",
            "/api/v1/users/self/files",
            data=[
                ("name", filename),
                ("size", str(size)),
                ("content_type", content_type),
                ("parent_folder_path", parent_folder_path),
                ("on_duplicate", on_duplicate),
            ],
            expected_status=(200, 201),
        )
        if not isinstance(payload, dict) or not payload.get("upload_url") or not payload.get("upload_params"):
            raise CanvasApiError(
                message="Canvas nao retornou o fluxo de upload esperado para o anexo.",
                details=payload,
            )
        return payload

    def upload_file_to_canvas(
        self,
        *,
        upload_url: str,
        upload_params: dict,
        file_path: str,
        filename: str,
        content_type: str,
    ) -> dict:
        multipart_data = [(str(key), str(value)) for key, value in (upload_params or {}).items()]
        with Path(file_path).open("rb") as file_handle:
            _payload, response = self._request(
                "POST",
                upload_url,
                data=multipart_data,
                files={
                    "file": (
                        filename,
                        file_handle,
                        content_type or "application/octet-stream",
                    )
                },
                headers={"Accept": "application/json"},
                use_auth=False,
                allow_redirects=False,
                expected_status=(200, 201, 301, 302, 303),
            )

        location = response.headers.get("Location")
        if response.status_code in {301, 302, 303}:
            if not location:
                raise CanvasApiError(
                    message="Canvas nao retornou a URL final do upload do anexo.",
                    status_code=response.status_code,
                )
            payload, _ = self._request("GET", location, expected_status=(200, 201))
            if not isinstance(payload, dict):
                raise CanvasApiError(message="Canvas nao retornou o arquivo anexado em JSON.", details=payload)
            return payload

        if response.status_code == 201 and location:
            payload, _ = self._request("GET", location, expected_status=(200, 201))
            if not isinstance(payload, dict):
                raise CanvasApiError(message="Canvas nao retornou o arquivo anexado em JSON.", details=payload)
            return payload

        payload = self._extract_json_or_text(response)
        if not isinstance(payload, dict):
            raise CanvasApiError(message="Upload do anexo concluiu sem retornar JSON de arquivo.", details=payload)
        return payload

    def upload_conversation_attachment(
        self,
        *,
        file_path: str,
        filename: str,
        content_type: str,
        size: int,
    ) -> dict:
        upload_start = self.initiate_user_file_upload(
            filename=filename,
            size=size,
            content_type=content_type,
            parent_folder_path="conversation attachments",
            on_duplicate="rename",
        )
        return self.upload_file_to_canvas(
            upload_url=upload_start["upload_url"],
            upload_params=upload_start["upload_params"],
            file_path=file_path,
            filename=filename,
            content_type=content_type,
        )
