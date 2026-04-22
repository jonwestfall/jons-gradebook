from __future__ import annotations

from datetime import datetime, timezone

from dateutil import parser
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Assignment,
    AssignmentGroup,
    AssignmentSource,
    CanvasAssignmentSnapshot,
    CanvasCourseSnapshot,
    CanvasEnrollmentSnapshot,
    CanvasSubmissionSnapshot,
    CanvasSyncRun,
    Course,
    Enrollment,
    EnrollmentRole,
    GradeEntry,
    GradeSource,
    GradeStatus,
    StudentProfile,
    SyncStatus,
    SyncTrigger,
)
from app.services.canvas.client import CanvasReadClient
from app.services.canvas.student_mapping import get_effective_mapping, resolve_student_fields
from app.services.canvas.selection import selected_course_ids


def _parse_datetime(value: str | None):
    if not value:
        return None
    return parser.isoparse(value)


def _split_name(full_name: str) -> tuple[str, str]:
    parts = (full_name or "").strip().split()
    if not parts:
        return "Unknown", "Student"
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def run_canvas_sync(
    db: Session,
    trigger_type: SyncTrigger,
    snapshot_label: str | None = None,
    canvas_course_ids: list[str] | None = None,
) -> CanvasSyncRun:
    run = CanvasSyncRun(
        trigger_type=trigger_type,
        status=SyncStatus.started,
        started_at=datetime.now(timezone.utc),
        snapshot_label=snapshot_label,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    client = CanvasReadClient()
    field_mapping = get_effective_mapping(db)

    try:
        if not client.configured:
            run.status = SyncStatus.failed
            run.error_message = "Canvas credentials not configured"
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            return run

        target_ids = {str(course_id) for course_id in (canvas_course_ids or selected_course_ids(db))}
        if not target_ids:
            run.status = SyncStatus.failed
            run.error_message = "No selected Canvas courses. Use Add Classes to choose courses before syncing."
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(run)
            return run

        courses = client.fetch_courses()
        courses = [course for course in courses if str(course.get("id")) in target_ids]

        if not courses:
            run.status = SyncStatus.failed
            run.error_message = "No accessible Canvas courses matched your current selection."
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(run)
            return run

        for course_payload in courses:
            canvas_course_id = str(course_payload["id"])

            db.add(
                CanvasCourseSnapshot(
                    sync_run_id=run.id,
                    canvas_course_id=canvas_course_id,
                    name=course_payload.get("name", "Untitled Course"),
                    section_name=course_payload.get("course_code"),
                    payload=course_payload,
                )
            )

            course = db.scalar(select(Course).where(Course.canvas_course_id == canvas_course_id))
            if not course:
                course = Course(
                    canvas_course_id=canvas_course_id,
                    name=course_payload.get("name", "Untitled Course"),
                    section_name=course_payload.get("course_code"),
                    term_name=(course_payload.get("term") or {}).get("name"),
                    is_active=True,
                )
                db.add(course)
                db.flush()
            else:
                course.name = course_payload.get("name", course.name)
                course.section_name = course_payload.get("course_code", course.section_name)
                course.term_name = (course_payload.get("term") or {}).get("name") or course.term_name

            enrollments = client.fetch_enrollments(canvas_course_id)
            for enrollment_payload in enrollments:
                user_payload = enrollment_payload.get("user") or {}
                canvas_user_id = str(user_payload.get("id") or enrollment_payload.get("user_id"))
                resolved_fields = resolve_student_fields(enrollment_payload, field_mapping)
                full_name = user_payload.get("name") or enrollment_payload.get("user", {}).get("short_name", "")
                split_first, split_last = _split_name(full_name)
                first_name = resolved_fields.get("first_name") or split_first
                last_name = resolved_fields.get("last_name") or split_last

                db.add(
                    CanvasEnrollmentSnapshot(
                        sync_run_id=run.id,
                        canvas_course_id=canvas_course_id,
                        canvas_enrollment_id=str(enrollment_payload["id"]),
                        canvas_user_id=canvas_user_id,
                        role=enrollment_payload.get("type"),
                        payload=enrollment_payload,
                    )
                )

                student = db.scalar(select(StudentProfile).where(StudentProfile.canvas_user_id == canvas_user_id))
                if not student:
                    student = StudentProfile(
                        canvas_user_id=canvas_user_id,
                        first_name=first_name,
                        last_name=last_name,
                        email=resolved_fields.get("email"),
                        student_number=resolved_fields.get("student_number"),
                        institution_name=resolved_fields.get("institution_name"),
                    )
                    db.add(student)
                    db.flush()
                else:
                    student.first_name = first_name or student.first_name
                    student.last_name = last_name or student.last_name
                    student.email = resolved_fields.get("email") or student.email
                    student.student_number = resolved_fields.get("student_number") or student.student_number
                    student.institution_name = resolved_fields.get("institution_name") or student.institution_name

                enrollment = db.scalar(
                    select(Enrollment).where(Enrollment.course_id == course.id, Enrollment.student_id == student.id)
                )
                if not enrollment:
                    enrollment = Enrollment(
                        course_id=course.id,
                        student_id=student.id,
                        role=EnrollmentRole.student,
                        canvas_enrollment_id=str(enrollment_payload["id"]),
                    )
                    db.add(enrollment)

            assignments = client.fetch_assignments(canvas_course_id)
            for assignment_payload in assignments:
                canvas_assignment_id = str(assignment_payload["id"])
                db.add(
                    CanvasAssignmentSnapshot(
                        sync_run_id=run.id,
                        canvas_course_id=canvas_course_id,
                        canvas_assignment_id=canvas_assignment_id,
                        name=assignment_payload.get("name", "Untitled Assignment"),
                        due_at=_parse_datetime(assignment_payload.get("due_at")),
                        points_possible=assignment_payload.get("points_possible"),
                        payload=assignment_payload,
                    )
                )

                group_canvas_id = assignment_payload.get("assignment_group_id")
                group = None
                if group_canvas_id is not None:
                    group_name = f"Canvas Group {group_canvas_id}"
                    group = db.scalar(
                        select(AssignmentGroup).where(
                            AssignmentGroup.course_id == course.id,
                            AssignmentGroup.name == group_name,
                        )
                    )
                    if not group:
                        group = AssignmentGroup(course_id=course.id, name=group_name)
                        db.add(group)
                        db.flush()

                assignment = db.scalar(
                    select(Assignment).where(
                        Assignment.course_id == course.id,
                        Assignment.canvas_assignment_id == canvas_assignment_id,
                    )
                )
                if not assignment:
                    assignment = Assignment(
                        course_id=course.id,
                        assignment_group_id=group.id if group else None,
                        source=AssignmentSource.canvas,
                        canvas_assignment_id=canvas_assignment_id,
                        title=assignment_payload.get("name", "Untitled Assignment"),
                        description=assignment_payload.get("description"),
                        due_at=_parse_datetime(assignment_payload.get("due_at")),
                        points_possible=assignment_payload.get("points_possible"),
                        is_archived=False,
                        is_hidden=False,
                    )
                    db.add(assignment)
                    db.flush()
                else:
                    assignment.assignment_group_id = group.id if group else assignment.assignment_group_id
                    assignment.title = assignment_payload.get("name", assignment.title)
                    assignment.description = assignment_payload.get("description", assignment.description)
                    assignment.due_at = _parse_datetime(assignment_payload.get("due_at"))
                    assignment.points_possible = assignment_payload.get("points_possible")

            grouped_submissions = client.fetch_grouped_gradebook_submissions(canvas_course_id)
            for student_submission_payload in grouped_submissions:
                canvas_user_id = str(student_submission_payload.get("user_id"))
                student = db.scalar(select(StudentProfile).where(StudentProfile.canvas_user_id == canvas_user_id))
                if not student:
                    # If Canvas returns submissions for a student not present in enrollment payload,
                    # create a minimal profile so grade rows are not dropped.
                    student = StudentProfile(
                        canvas_user_id=canvas_user_id,
                        first_name="Unknown",
                        last_name="Student",
                        email=None,
                        student_number=None,
                        institution_name=None,
                    )
                    db.add(student)
                    db.flush()

                for submission_payload in student_submission_payload.get("submissions", []):
                    assignment_payload = submission_payload.get("assignment") or {}
                    if not assignment_payload.get("id"):
                        continue

                    canvas_assignment_id = str(assignment_payload["id"])
                    assignment = db.scalar(
                        select(Assignment).where(
                            Assignment.course_id == course.id,
                            Assignment.canvas_assignment_id == canvas_assignment_id,
                        )
                    )
                    if not assignment:
                        assignment = Assignment(
                            course_id=course.id,
                            assignment_group_id=None,
                            source=AssignmentSource.canvas,
                            canvas_assignment_id=canvas_assignment_id,
                            title=assignment_payload.get("name", "Untitled Assignment"),
                            description=assignment_payload.get("description"),
                            due_at=_parse_datetime(assignment_payload.get("due_at")),
                            points_possible=assignment_payload.get("points_possible"),
                            is_archived=False,
                            is_hidden=False,
                        )
                        db.add(assignment)
                        db.flush()

                    score = submission_payload.get("score")
                    missing = bool(submission_payload.get("missing", False))
                    excused = bool(submission_payload.get("excused", False))

                    db.add(
                        CanvasSubmissionSnapshot(
                            sync_run_id=run.id,
                            canvas_course_id=canvas_course_id,
                            canvas_assignment_id=canvas_assignment_id,
                            canvas_user_id=canvas_user_id,
                            score=score,
                            submitted_at=_parse_datetime(submission_payload.get("submitted_at")),
                            payload=submission_payload,
                        )
                    )

                    status = GradeStatus.graded
                    if excused:
                        status = GradeStatus.excused
                    elif missing:
                        status = GradeStatus.missing
                    elif score is None:
                        status = GradeStatus.unsubmitted

                    grade = db.scalar(
                        select(GradeEntry).where(
                            GradeEntry.assignment_id == assignment.id,
                            GradeEntry.student_id == student.id,
                        )
                    )
                    if not grade:
                        grade = GradeEntry(
                            assignment_id=assignment.id,
                            student_id=student.id,
                            source=GradeSource.canvas,
                            status=status,
                            score=score,
                            submitted_at=_parse_datetime(submission_payload.get("submitted_at")),
                            snapshot_run_id=run.id,
                        )
                        db.add(grade)
                    else:
                        grade.source = GradeSource.canvas
                        grade.status = status
                        grade.score = score
                        grade.submitted_at = _parse_datetime(submission_payload.get("submitted_at"))
                        grade.snapshot_run_id = run.id

        run.status = SyncStatus.completed
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return run

    except Exception as exc:
        run.status = SyncStatus.failed
        run.error_message = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return run
