from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.db.models import (
    Assignment,
    AttendanceRecord,
    Course,
    Enrollment,
    GradeEntry,
    InteractionLog,
    RubricEvaluation,
    RubricTemplate,
    StudentProfile,
)


BRAND_TITLE = "Jon's Gradebook"


def _student_summary(
    db: Session,
    student_id: int,
    include_all_rubrics: bool = True,
    rubric_id: int | None = None,
    assignment_id: int | None = None,
) -> dict:
    student = db.scalar(
        select(StudentProfile)
        .where(StudentProfile.id == student_id)
        .options(joinedload(StudentProfile.enrollments).joinedload(Enrollment.course))
    )
    if not student:
        raise ValueError("Student not found")

    attendance_rows = db.scalars(select(AttendanceRecord).where(AttendanceRecord.student_id == student_id)).all()
    attendance_counts = Counter(record.status.value for record in attendance_rows)

    interaction_rows = db.scalars(
        select(InteractionLog).where(InteractionLog.student_profile_id == student_id).order_by(InteractionLog.occurred_at.desc())
    ).all()

    grade_rows = db.execute(
        select(GradeEntry, Assignment)
        .join(Assignment, GradeEntry.assignment_id == Assignment.id)
        .where(GradeEntry.student_id == student_id)
    ).all()
    grade_overview_by_course: dict[int, dict] = defaultdict(
        lambda: {
            "course_name": "Unknown Course",
            "earned": 0.0,
            "possible": 0.0,
            "graded_items": 0,
        }
    )
    for grade, assignment in grade_rows:
        bucket = grade_overview_by_course[assignment.course_id]
        bucket["course_name"] = next(
            (enrollment.course.name for enrollment in student.enrollments if enrollment.course_id == assignment.course_id),
            f"Course {assignment.course_id}",
        )
        if assignment.points_possible is not None:
            bucket["possible"] += float(assignment.points_possible)
        if grade.score is not None:
            bucket["earned"] += float(grade.score)
            bucket["graded_items"] += 1

    grade_overview = []
    for course_id, bucket in grade_overview_by_course.items():
        possible = float(bucket["possible"])
        earned = float(bucket["earned"])
        grade_overview.append(
            {
                "course_id": course_id,
                "course_name": bucket["course_name"],
                "earned": round(earned, 2),
                "possible": round(possible, 2),
                "percent": round((earned / possible) * 100.0, 2) if possible > 0 else None,
                "graded_items": int(bucket["graded_items"]),
            }
        )
    grade_overview.sort(key=lambda row: row["course_name"])

    rubric_query = (
        select(RubricEvaluation)
        .where(RubricEvaluation.student_profile_id == student_id)
        .order_by(RubricEvaluation.created_at.desc())
    )
    if not include_all_rubrics:
        if rubric_id is not None:
            rubric_query = rubric_query.where(RubricEvaluation.rubric_id == rubric_id)
        if assignment_id is not None:
            rubric_query = rubric_query.where(RubricEvaluation.assignment_id == assignment_id)
    rubric_evals = db.scalars(rubric_query.limit(50)).all()

    rubric_ids = {evaluation.rubric_id for evaluation in rubric_evals}
    rubric_map = {
        rubric.id: rubric
        for rubric in (db.scalars(select(RubricTemplate).where(RubricTemplate.id.in_(rubric_ids))).all() if rubric_ids else [])
    }
    course_ids = {evaluation.course_id for evaluation in rubric_evals if evaluation.course_id is not None}
    assignment_ids = {evaluation.assignment_id for evaluation in rubric_evals if evaluation.assignment_id is not None}
    course_map = {
        course.id: course
        for course in (db.scalars(select(Course).where(Course.id.in_(course_ids))).all() if course_ids else [])
    }
    assignment_map = {
        assignment.id: assignment
        for assignment in (
            db.scalars(select(Assignment).where(Assignment.id.in_(assignment_ids))).all() if assignment_ids else []
        )
    }

    return {
        "student": student,
        "courses": [enrollment.course.name for enrollment in student.enrollments],
        "grade_overview": grade_overview,
        "attendance": dict(attendance_counts),
        "rubric_scope": {
            "include_all_rubrics": include_all_rubrics,
            "rubric_id": rubric_id,
            "assignment_id": assignment_id,
        },
        "rubric_evaluations": [
            {
                "id": evaluation.id,
                "rubric_name": rubric_map.get(evaluation.rubric_id).name if rubric_map.get(evaluation.rubric_id) else None,
                "total_points": evaluation.total_points,
                "max_points": rubric_map.get(evaluation.rubric_id).max_points if rubric_map.get(evaluation.rubric_id) else None,
                "course_name": course_map.get(evaluation.course_id).name if evaluation.course_id and course_map.get(evaluation.course_id) else None,
                "assignment_title": assignment_map.get(evaluation.assignment_id).title if evaluation.assignment_id and assignment_map.get(evaluation.assignment_id) else None,
                "created_at": evaluation.created_at.isoformat(),
            }
            for evaluation in rubric_evals
        ],
        "recent_interactions": [
            {
                "type": interaction.interaction_type.value,
                "summary": interaction.summary,
                "occurred_at": interaction.occurred_at.isoformat(),
            }
            for interaction in interaction_rows[:10]
        ],
    }


def _draw_pdf(report_path: Path, summary: dict) -> None:
    pdf = canvas.Canvas(str(report_path), pagesize=LETTER)
    _, height = LETTER

    student = summary["student"]

    y = height - 60
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, f"{BRAND_TITLE} - Student Report")

    y -= 30
    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Student: {student.first_name} {student.last_name}")
    y -= 18
    pdf.drawString(50, y, f"Email: {student.email or 'N/A'}")
    y -= 18
    pdf.drawString(50, y, "Courses: " + (", ".join(summary["courses"]) or "None"))

    scope_label = "All rubrics"
    if not summary["rubric_scope"].get("include_all_rubrics"):
        parts = []
        if summary["rubric_scope"].get("rubric_id"):
            parts.append(f"Rubric #{summary['rubric_scope']['rubric_id']}")
        if summary["rubric_scope"].get("assignment_id"):
            parts.append(f"Assignment #{summary['rubric_scope']['assignment_id']}")
        scope_label = " + ".join(parts) if parts else "Filtered"
    y -= 18
    pdf.drawString(50, y, f"Rubric scope: {scope_label}")

    y -= 30
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Grade Overview")
    y -= 18
    pdf.setFont("Helvetica", 10)
    if summary["grade_overview"]:
        for row in summary["grade_overview"][:8]:
            percent = f"{row['percent']}%" if row["percent"] is not None else "N/A"
            line = f"- {row['course_name']}: {row['earned']}/{row['possible']} ({percent})"
            pdf.drawString(60, y, line[:110])
            y -= 14
            if y < 90:
                pdf.showPage()
                y = height - 60
                pdf.setFont("Helvetica", 10)
    else:
        pdf.drawString(60, y, "No grade data available")
        y -= 14

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Attendance")
    y -= 18
    pdf.setFont("Helvetica", 11)
    for status in ("present", "absent", "tardy", "excused"):
        pdf.drawString(60, y, f"{status.title()}: {summary['attendance'].get(status, 0)}")
        y -= 16

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Rubric Evaluations")
    y -= 18
    pdf.setFont("Helvetica", 10)
    if summary["rubric_evaluations"]:
        for evaluation in summary["rubric_evaluations"][:12]:
            score = (
                f"{evaluation['total_points']}/{evaluation['max_points']}"
                if evaluation["total_points"] is not None and evaluation["max_points"] is not None
                else (str(evaluation["total_points"]) if evaluation["total_points"] is not None else "N/A")
            )
            target = evaluation["assignment_title"] or evaluation["course_name"] or "General"
            line = f"- {evaluation['created_at'][:10]} [{evaluation['rubric_name'] or 'Rubric'}] {score} - {target}"
            pdf.drawString(60, y, line[:110])
            y -= 14
            if y < 90:
                pdf.showPage()
                y = height - 60
                pdf.setFont("Helvetica", 10)
    else:
        pdf.drawString(60, y, "No rubric evaluations available")
        y -= 14

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y, "Recent Interactions")
    y -= 18
    pdf.setFont("Helvetica", 10)

    for interaction in summary["recent_interactions"][:10]:
        line = f"- {interaction['occurred_at'][:10]} [{interaction['type']}] {interaction['summary']}"
        pdf.drawString(60, y, line[:110])
        y -= 14
        if y < 70:
            pdf.showPage()
            y = height - 60

    pdf.save()


def _draw_png(image_path: Path, summary: dict) -> None:
    image = Image.new("RGB", (1200, 1600), "#f5f7fb")
    draw = ImageDraw.Draw(image)
    font_title = ImageFont.load_default()
    font_body = ImageFont.load_default()

    student = summary["student"]

    y = 40
    draw.text((40, y), f"{BRAND_TITLE} - Student Report", fill="#1b2840", font=font_title)
    y += 50
    draw.text((40, y), f"Student: {student.first_name} {student.last_name}", fill="#14213d", font=font_body)
    y += 24
    draw.text((40, y), f"Email: {student.email or 'N/A'}", fill="#14213d", font=font_body)
    y += 24
    draw.text((40, y), "Courses: " + (", ".join(summary["courses"]) or "None"), fill="#14213d", font=font_body)

    scope_label = "All rubrics"
    if not summary["rubric_scope"].get("include_all_rubrics"):
        parts = []
        if summary["rubric_scope"].get("rubric_id"):
            parts.append(f"Rubric #{summary['rubric_scope']['rubric_id']}")
        if summary["rubric_scope"].get("assignment_id"):
            parts.append(f"Assignment #{summary['rubric_scope']['assignment_id']}")
        scope_label = " + ".join(parts) if parts else "Filtered"
    y += 24
    draw.text((40, y), f"Rubric scope: {scope_label}", fill="#14213d", font=font_body)

    y += 36
    draw.text((40, y), "Grade Overview", fill="#1b2840", font=font_title)
    y += 26
    for row in summary["grade_overview"][:5]:
        percent = f"{row['percent']}%" if row["percent"] is not None else "N/A"
        line = f"{row['course_name']}: {row['earned']}/{row['possible']} ({percent})"
        draw.text((50, y), line[:140], fill="#27314f", font=font_body)
        y += 20

    if not summary["grade_overview"]:
        draw.text((50, y), "No grade data available", fill="#27314f", font=font_body)
        y += 20

    y += 16
    draw.text((40, y), "Attendance", fill="#1b2840", font=font_title)
    y += 26
    for status in ("present", "absent", "tardy", "excused"):
        draw.text((50, y), f"{status.title()}: {summary['attendance'].get(status, 0)}", fill="#27314f", font=font_body)
        y += 20

    y += 16
    draw.text((40, y), "Rubric Evaluations", fill="#1b2840", font=font_title)
    y += 26

    for evaluation in summary["rubric_evaluations"][:9]:
        score = (
            f"{evaluation['total_points']}/{evaluation['max_points']}"
            if evaluation["total_points"] is not None and evaluation["max_points"] is not None
            else (str(evaluation["total_points"]) if evaluation["total_points"] is not None else "N/A")
        )
        target = evaluation["assignment_title"] or evaluation["course_name"] or "General"
        line = f"{evaluation['created_at'][:10]} [{evaluation['rubric_name'] or 'Rubric'}] {score} - {target}"
        draw.text((50, y), line[:140], fill="#27314f", font=font_body)
        y += 20

    if not summary["rubric_evaluations"]:
        draw.text((50, y), "No rubric evaluations available", fill="#27314f", font=font_body)
        y += 20

    y += 16
    draw.text((40, y), "Recent Interactions", fill="#1b2840", font=font_title)
    y += 26

    for interaction in summary["recent_interactions"][:12]:
        line = f"{interaction['occurred_at'][:10]} [{interaction['type']}] {interaction['summary']}"
        draw.text((50, y), line[:140], fill="#27314f", font=font_body)
        y += 20

    image.save(image_path, format="PNG")


def generate_student_report(
    db: Session,
    student_id: int,
    basename: str = "student-report",
    include_all_rubrics: bool = True,
    rubric_id: int | None = None,
    assignment_id: int | None = None,
) -> dict[str, str]:
    settings = get_settings()
    output_root = Path(settings.storage_root) / "reports" / str(student_id)
    output_root.mkdir(parents=True, exist_ok=True)

    summary = _student_summary(
        db,
        student_id,
        include_all_rubrics=include_all_rubrics,
        rubric_id=rubric_id,
        assignment_id=assignment_id,
    )

    pdf_path = output_root / f"{basename}.pdf"
    png_path = output_root / f"{basename}.png"

    _draw_pdf(pdf_path, summary)
    _draw_png(png_path, summary)

    return {
        "pdf_path": str(pdf_path),
        "png_path": str(png_path),
    }
