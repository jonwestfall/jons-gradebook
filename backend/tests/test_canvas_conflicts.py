from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import (
    Assignment,
    AssignmentGradingType,
    AssignmentSource,
    CanvasSubmissionSnapshot,
    CanvasSyncConflict,
    CanvasSyncRun,
    Course,
    GradeEntry,
    GradeSource,
    GradeStatus,
    StudentProfile,
    SyncStatus,
    SyncTrigger,
)


def _seed_conflict(db: Session) -> CanvasSyncConflict:
    course = Course(name="Biology 101", canvas_course_id="course-1")
    student = StudentProfile(first_name="Ada", last_name="Lovelace", canvas_user_id="user-1")
    assignment = Assignment(
        course=course,
        source=AssignmentSource.canvas,
        canvas_assignment_id="assignment-1",
        title="Lab Report",
        grading_type=AssignmentGradingType.points,
        points_possible=10,
    )
    run = CanvasSyncRun(
        trigger_type=SyncTrigger.manual,
        status=SyncStatus.completed,
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
    )
    db.add_all([course, student, assignment, run])
    db.flush()
    grade = GradeEntry(
        assignment_id=assignment.id,
        student_id=student.id,
        source=GradeSource.manual_override,
        status=GradeStatus.graded,
        score=7,
    )
    snapshot = CanvasSubmissionSnapshot(
        sync_run_id=run.id,
        canvas_course_id="course-1",
        canvas_assignment_id="assignment-1",
        canvas_user_id="user-1",
        score=9,
        payload={"score": 9},
    )
    db.add_all([grade, snapshot])
    db.flush()
    conflict = CanvasSyncConflict(
        sync_run_id=run.id,
        course_id=course.id,
        assignment_id=assignment.id,
        student_id=student.id,
        grade_entry_id=grade.id,
        submission_snapshot_id=snapshot.id,
        canvas_course_id="course-1",
        canvas_assignment_id="assignment-1",
        canvas_user_id="user-1",
        local_score=7,
        canvas_score=9,
        local_status="graded",
        canvas_status="graded",
        local_source="manual_override",
    )
    db.add(conflict)
    db.commit()
    return conflict


def test_lists_and_resolves_canvas_conflict(client, db_session: Session):
    conflict = _seed_conflict(db_session)

    response = client.get(f"/api/v1/canvas/sync/runs/{conflict.sync_run_id}/conflicts")
    assert response.status_code == 200
    rows = response.json()
    assert rows[0]["local"]["score"] == 7
    assert rows[0]["canvas"]["score"] == 9

    response = client.post(
        f"/api/v1/canvas/sync/conflicts/{conflict.id}/resolve",
        json={"status": "kept_local", "rationale": "Instructor note is newer."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "kept_local"
    assert response.json()["rationale"] == "Instructor note is newer."


def test_accepting_canvas_conflict_updates_grade_and_audit(client, db_session: Session):
    conflict = _seed_conflict(db_session)

    response = client.post(
        f"/api/v1/canvas/sync/conflicts/{conflict.id}/resolve",
        json={"status": "accepted_canvas", "rationale": "Canvas submission is authoritative."},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted_canvas"

    db_session.refresh(conflict.grade_entry)
    assert conflict.grade_entry.score == 9
    assert conflict.grade_entry.source == GradeSource.canvas
