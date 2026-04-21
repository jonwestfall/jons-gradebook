from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Advisee, Course, StudentProfile


EMAIL_REGEX = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
ID_REGEX = re.compile(r"\b(?:ID[:\s-]*)?[A-Z0-9]{6,}\b")


@dataclass
class DeidentifyResult:
    original_text: str
    preview_text: str
    replacements: dict[str, str]


class DeidentifyService:
    def __init__(self, db: Session):
        self.db = db

    def _collect_named_entities(self) -> Iterable[tuple[str, str]]:
        entities: list[tuple[str, str]] = []

        students = self.db.scalars(select(StudentProfile)).all()
        for idx, student in enumerate(students, start=1):
            full_name = f"{student.first_name} {student.last_name}".strip()
            if full_name:
                entities.append((full_name, f"[NAME_{idx}]"))
            if student.email:
                entities.append((student.email, f"[EMAIL_{idx}]"))
            if student.student_number:
                entities.append((student.student_number, f"[ID_{idx}]"))
            if student.institution_name:
                entities.append((student.institution_name, f"[INSTITUTION_{idx}]"))

        advisees = self.db.scalars(select(Advisee)).all()
        for idx, advisee in enumerate(advisees, start=1):
            full_name = f"{advisee.first_name} {advisee.last_name}".strip()
            if full_name:
                entities.append((full_name, f"[ADVISEE_{idx}]"))
            if advisee.email:
                entities.append((advisee.email, f"[ADVISEE_EMAIL_{idx}]"))
            if advisee.external_id:
                entities.append((advisee.external_id, f"[ADVISEE_ID_{idx}]"))

        courses = self.db.scalars(select(Course)).all()
        for idx, course in enumerate(courses, start=1):
            if course.name:
                entities.append((course.name, f"[COURSE_{idx}]"))
            if course.section_name:
                entities.append((course.section_name, f"[SECTION_{idx}]"))

        return entities

    def apply(self, text: str) -> DeidentifyResult:
        replacements: dict[str, str] = {}
        output = text

        entities = sorted(self._collect_named_entities(), key=lambda item: len(item[0]), reverse=True)
        for original, token in entities:
            if original and original in output:
                output = output.replace(original, token)
                replacements[token] = original

        for idx, email in enumerate(sorted(set(EMAIL_REGEX.findall(output))), start=1):
            token = f"[EMAIL_REGEX_{idx}]"
            output = output.replace(email, token)
            replacements[token] = email

        for idx, identifier in enumerate(sorted(set(ID_REGEX.findall(output))), start=1):
            if identifier.startswith("[") and identifier.endswith("]"):
                continue
            token = f"[GENERIC_ID_{idx}]"
            output = output.replace(identifier, token)
            replacements[token] = identifier

        return DeidentifyResult(original_text=text, preview_text=output, replacements=replacements)
