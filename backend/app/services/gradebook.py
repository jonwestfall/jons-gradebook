from __future__ import annotations

from collections import defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    Assignment,
    AssignmentGradingType,
    Course,
    CourseGradeRule,
    Enrollment,
    EnrollmentRole,
    GradebookCalculatedColumn,
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
            joinedload(Course.calculated_columns),
            joinedload(Course.enrollments).joinedload(Enrollment.student),
            joinedload(Course.grade_rules).joinedload(CourseGradeRule.template),
        )
    )
    if not course:
        raise ValueError("Course not found")

    assignments = [a for a in course.assignments if not a.is_archived and (include_hidden or not a.is_hidden)]
    assignments.sort(key=lambda item: (item.display_order, item.id))
    calculated_columns = sorted(course.calculated_columns, key=lambda item: (item.display_order, item.id))
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
            letter_grade = grade.letter_grade if grade else None
            completion_status = grade.completion_status.value if grade and grade.completion_status else None
            status = grade.status.value if grade else GradeStatus.unsubmitted.value
            dropped = assignment.id in dropped_ids

            if assignment.grading_type == AssignmentGradingType.points and assignment.points_possible and not dropped:
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
                    "grading_type": assignment.grading_type.value,
                    "status": status,
                    "score": score,
                    "letter_grade": letter_grade,
                    "completion_status": completion_status,
                    "grade_source": grade.source.value if grade else None,
                    "is_out_of_sync": bool(
                        assignment.source.value == "canvas"
                        and grade is not None
                        and grade.source.value in {"local", "manual_override"}
                    ),
                    "dropped_by_rule": dropped,
                }
            )

        calculated_values: list[dict[str, Any]] = []
        assignment_map = {assignment.id: assignment for assignment in assignments}
        payload_map = {item["assignment_id"]: item for item in assignments_payload}
        for column in calculated_columns:
            selected_ids = [assignment_id for assignment_id in column.assignment_ids if assignment_id in assignment_map]
            value: float | None = None
            display: str = "N/A"

            if column.operation.value == "sum_points":
                total = 0.0
                matched = False
                for assignment_id in selected_ids:
                    assignment = assignment_map[assignment_id]
                    if assignment.grading_type != AssignmentGradingType.points:
                        continue
                    score = payload_map.get(assignment_id, {}).get("score")
                    if score is not None:
                        total += float(score)
                        matched = True
                if matched:
                    value = round(total, 2)
                    display = str(value)

            elif column.operation.value == "average_percent":
                percents: list[float] = []
                for assignment_id in selected_ids:
                    assignment = assignment_map[assignment_id]
                    payload_item = payload_map.get(assignment_id, {})
                    if assignment.grading_type == AssignmentGradingType.points:
                        score = payload_item.get("score")
                        points_possible = payload_item.get("points_possible")
                        if score is not None and points_possible:
                            percents.append(float(score) / float(points_possible) * 100.0)
                    elif assignment.grading_type == AssignmentGradingType.letter:
                        letter = (payload_item.get("letter_grade") or "").upper().strip()
                        mapping = {"A+": 100, "A": 95, "A-": 90, "B+": 88, "B": 85, "B-": 80, "C+": 78, "C": 75, "C-": 70, "D+": 68, "D": 65, "D-": 60, "F": 50}
                        if letter in mapping:
                            percents.append(float(mapping[letter]))
                    else:
                        completion = payload_item.get("completion_status")
                        if completion == "complete":
                            percents.append(100.0)
                        elif completion in {"incomplete", "missing"}:
                            percents.append(0.0)
                if percents:
                    value = round(sum(percents) / len(percents), 2)
                    display = f"{value}%"

            elif column.operation.value == "completion_rate":
                complete = 0
                eligible = 0
                for assignment_id in selected_ids:
                    assignment = assignment_map[assignment_id]
                    if assignment.grading_type != AssignmentGradingType.completion:
                        continue
                    completion = payload_map.get(assignment_id, {}).get("completion_status")
                    if completion is None:
                        continue
                    eligible += 1
                    if completion == "complete":
                        complete += 1
                if eligible > 0:
                    value = round((complete / eligible) * 100.0, 2)
                    display = f"{value}%"

            calculated_values.append(
                {
                    "column_id": column.id,
                    "name": column.name,
                    "operation": column.operation.value,
                    "value": value,
                    "display": display,
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
                "calculated_values": calculated_values,
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
                "grading_type": assignment.grading_type.value,
                "assignment_group_id": assignment.assignment_group_id,
                "is_hidden": assignment.is_hidden,
                "is_archived": assignment.is_archived,
            }
            for assignment in assignments
        ],
        "calculated_columns": [
            {
                "id": column.id,
                "name": column.name,
                "operation": column.operation.value,
                "assignment_ids": column.assignment_ids,
                "display_order": column.display_order,
            }
            for column in calculated_columns
        ],
        "students": students_payload,
        "rules_applied": rule_config,
    }
