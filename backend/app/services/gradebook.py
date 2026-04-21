from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    Assignment,
    Course,
    CourseGradeRule,
    Enrollment,
    EnrollmentRole,
    GradeEntry,
    GradeStatus,
    RuleType,
)


def _build_rule_config(course_rules: list[CourseGradeRule]) -> dict[str, dict[str, Any]]:
    config: dict[str, dict[str, Any]] = {}
    for course_rule in course_rules:
        if not course_rule.is_enabled or not course_rule.template.is_active:
            continue
        config[course_rule.template.rule_type.value] = course_rule.template.config
    return config


def build_merged_gradebook(db: Session, course_id: int, include_hidden: bool = False) -> dict[str, Any]:
    course = db.scalar(
        select(Course)
        .where(Course.id == course_id)
        .options(
            joinedload(Course.assignments),
            joinedload(Course.enrollments).joinedload(Enrollment.student),
            joinedload(Course.grade_rules).joinedload(CourseGradeRule.template),
        )
    )
    if not course:
        raise ValueError("Course not found")

    assignments = [a for a in course.assignments if not a.is_archived and (include_hidden or not a.is_hidden)]
    assignment_ids = [a.id for a in assignments]

    grade_entries = db.scalars(select(GradeEntry).where(GradeEntry.assignment_id.in_(assignment_ids))).all() if assignment_ids else []
    by_student_assignment: dict[tuple[int, int], GradeEntry] = {(g.student_id, g.assignment_id): g for g in grade_entries}

    student_enrollments = [e for e in course.enrollments if e.role == EnrollmentRole.student]
    rule_config = _build_rule_config(course.grade_rules)

    drop_lowest_config = rule_config.get(RuleType.drop_lowest_in_group.value, {})
    drop_count = int(drop_lowest_config.get("count", 1))

    required_gate_config = rule_config.get(RuleType.required_completion_gate.value, {})
    required_assignment_ids = set(required_gate_config.get("required_assignment_ids", []))

    assignment_groups: dict[int | None, list[Assignment]] = defaultdict(list)
    for assignment in assignments:
        assignment_groups[assignment.assignment_group_id].append(assignment)

    students_payload: list[dict[str, Any]] = []

    for enrollment in student_enrollments:
        student = enrollment.student
        dropped_ids: set[int] = set()

        if drop_count > 0:
            for group_id, group_assignments in assignment_groups.items():
                if group_id is None:
                    continue
                scored = []
                for assignment in group_assignments:
                    entry = by_student_assignment.get((student.id, assignment.id))
                    if entry and entry.score is not None:
                        scored.append((assignment.id, entry.score))
                scored.sort(key=lambda item: item[1])
                for assignment_id, _score in scored[:drop_count]:
                    dropped_ids.add(assignment_id)

        assignments_payload: list[dict[str, Any]] = []
        total_points = 0.0
        total_earned = 0.0
        warnings: list[str] = []

        missing_required: list[str] = []

        for assignment in assignments:
            grade = by_student_assignment.get((student.id, assignment.id))
            score = grade.score if grade else None
            status = grade.status.value if grade else GradeStatus.unsubmitted.value
            dropped = assignment.id in dropped_ids

            if assignment.points_possible and not dropped:
                total_points += assignment.points_possible
                if score is not None:
                    total_earned += score

            if required_assignment_ids and assignment.id in required_assignment_ids:
                if status in {GradeStatus.unsubmitted.value, GradeStatus.missing.value}:
                    missing_required.append(assignment.title)

            assignments_payload.append(
                {
                    "assignment_id": assignment.id,
                    "title": assignment.title,
                    "source": assignment.source.value,
                    "due_at": assignment.due_at.isoformat() if assignment.due_at else None,
                    "points_possible": assignment.points_possible,
                    "status": status,
                    "score": score,
                    "dropped_by_rule": dropped,
                }
            )

        if missing_required:
            warnings.append(
                "Required completion gate warning: missing " + ", ".join(sorted(set(missing_required)))
            )

        percentage = (total_earned / total_points * 100.0) if total_points > 0 else None

        students_payload.append(
            {
                "student_id": student.id,
                "name": f"{student.first_name} {student.last_name}",
                "email": student.email,
                "assignments": assignments_payload,
                "totals": {
                    "earned": round(total_earned, 2),
                    "possible": round(total_points, 2),
                    "percent": round(percentage, 2) if percentage is not None else None,
                },
                "warnings": warnings,
            }
        )

    return {
        "course": {
            "id": course.id,
            "name": course.name,
            "section_name": course.section_name,
        },
        "assignments": [
            {
                "id": assignment.id,
                "title": assignment.title,
                "source": assignment.source.value,
                "due_at": assignment.due_at.isoformat() if assignment.due_at else None,
                "points_possible": assignment.points_possible,
                "assignment_group_id": assignment.assignment_group_id,
                "is_hidden": assignment.is_hidden,
                "is_archived": assignment.is_archived,
            }
            for assignment in assignments
        ],
        "students": students_payload,
        "rules_applied": rule_config,
    }
