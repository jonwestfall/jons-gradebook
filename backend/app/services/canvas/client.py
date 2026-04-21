from __future__ import annotations

from collections.abc import Iterator

import httpx

from app.core.config import get_settings


class CanvasReadClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.canvas_base_url.rstrip("/")
        self.token = settings.canvas_api_token

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    def _paginate(self, endpoint: str, params: dict | None = None) -> Iterator[dict]:
        if not self.configured:
            return iter(())

        url = f"{self.base_url}{endpoint}"
        while url:
            response = httpx.get(url, headers=self._headers(), params=params, timeout=60)
            response.raise_for_status()
            data = response.json()
            for row in data:
                yield row

            params = None
            links = response.links
            next_link = links.get("next") if links else None
            url = next_link["url"] if next_link else ""

    def fetch_courses(self) -> list[dict]:
        return list(
            self._paginate(
                "/api/v1/courses",
                params={
                    "enrollment_type": "teacher",
                    "include[]": ["term"],
                    "state[]": ["available", "completed", "created"],
                    "per_page": 100,
                },
            )
        )

    def fetch_assignments(self, canvas_course_id: str) -> list[dict]:
        return list(
            self._paginate(
                f"/api/v1/courses/{canvas_course_id}/assignments",
                params={"include[]": ["submission", "score_statistics"], "per_page": 100},
            )
        )

    def fetch_enrollments(self, canvas_course_id: str) -> list[dict]:
        return list(
            self._paginate(
                f"/api/v1/courses/{canvas_course_id}/enrollments",
                params={"type[]": ["StudentEnrollment"], "per_page": 100},
            )
        )

    def fetch_submissions(self, canvas_course_id: str, canvas_assignment_id: str) -> list[dict]:
        return list(
            self._paginate(
                f"/api/v1/courses/{canvas_course_id}/assignments/{canvas_assignment_id}/submissions",
                params={"per_page": 100},
            )
        )

    def fetch_grouped_gradebook_submissions(self, canvas_course_id: str) -> list[dict]:
        return list(
            self._paginate(
                f"/api/v1/courses/{canvas_course_id}/students/submissions",
                params={
                    "student_ids": "all",
                    "grouped": 1,
                    "include[]": ["assignment"],
                    "per_page": 100,
                },
            )
        )
