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


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = (text or "").split()
    lines: list[str] = []
    current = ""
    for word in words:
        next_line = f"{current} {word}".strip()
        if len(next_line) > max_chars and current:
            lines.append(current)
            current = word
        else:
            current = next_line
    if current:
        lines.append(current)
    return lines or [""]


def _score_label(total_points: float | None, max_points: float | None) -> str:
    if total_points is not None and max_points is not None:
        return f"{total_points}/{max_points}"
    if total_points is not None:
        return str(total_points)
    return "N/A"


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
    criterion_map = {
        criterion.id: criterion
        for rubric in rubric_map.values()
        for criterion in rubric.criteria
    }
    rating_map = {
        rating.id: rating
        for criterion in criterion_map.values()
        for rating in criterion.ratings
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
                "evaluator_notes": evaluation.evaluator_notes,
                "items": [
                    {
                        "id": item.id,
                        "criterion_id": item.criterion_id,
                        "criterion_title": criterion_map.get(item.criterion_id).title if criterion_map.get(item.criterion_id) else "Criterion",
                        "criterion_type": criterion_map.get(item.criterion_id).criterion_type.value if criterion_map.get(item.criterion_id) else None,
                        "criterion_max_points": criterion_map.get(item.criterion_id).max_points if criterion_map.get(item.criterion_id) else None,
                        "rating_id": item.rating_id,
                        "rating_title": rating_map.get(item.rating_id).title if item.rating_id and rating_map.get(item.rating_id) else None,
                        "rating_description": rating_map.get(item.rating_id).description if item.rating_id and rating_map.get(item.rating_id) else None,
                        "points_awarded": item.points_awarded,
                        "is_checked": item.is_checked,
                        "narrative_comment": item.narrative_comment,
                        "display_order": criterion_map.get(item.criterion_id).display_order if criterion_map.get(item.criterion_id) else 0,
                    }
                    for item in sorted(
                        evaluation.items,
                        key=lambda row: (criterion_map.get(row.criterion_id).display_order if criterion_map.get(row.criterion_id) else 0, row.id),
                    )
                ],
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
    y -= 20
    if summary["rubric_evaluations"]:
        for evaluation in summary["rubric_evaluations"][:6]:
            if y < 150:
                pdf.showPage()
                y = height - 60
            score = _score_label(evaluation["total_points"], evaluation["max_points"])
            target = evaluation["assignment_title"] or evaluation["course_name"] or "General"
            pdf.setFillColorRGB(0.96, 0.93, 0.86)
            pdf.roundRect(50, y - 28, 512, 32, 6, stroke=0, fill=1)
            pdf.setFillColorRGB(0.08, 0.21, 0.3)
            pdf.setFont("Helvetica-Bold", 10)
            pdf.drawString(60, y - 12, (evaluation["rubric_name"] or "Rubric")[:55])
            pdf.setFont("Helvetica", 9)
            pdf.drawRightString(552, y - 12, f"{score} | {evaluation['created_at'][:10]}")
            pdf.drawString(60, y - 24, target[:82])
            y -= 40
            for item in evaluation.get("items", [])[:6]:
                if y < 95:
                    pdf.showPage()
                    y = height - 60
                pdf.setStrokeColorRGB(0.84, 0.78, 0.66)
                pdf.setFillColorRGB(1, 0.99, 0.96)
                pdf.roundRect(60, y - 42, 492, 38, 4, stroke=1, fill=1)
                pdf.setFillColorRGB(0.12, 0.16, 0.22)
                pdf.setFont("Helvetica-Bold", 8.5)
                pdf.drawString(70, y - 16, (item["criterion_title"] or "Criterion")[:34])
                pdf.setFont("Helvetica", 8.5)
                rating = item.get("rating_title") or ("Checked" if item.get("is_checked") else "No rating")
                pdf.drawString(230, y - 16, rating[:35])
                points = _score_label(item.get("points_awarded"), item.get("criterion_max_points"))
                pdf.drawRightString(540, y - 16, points)
                detail = item.get("rating_description") or item.get("narrative_comment") or ""
                if detail:
                    pdf.drawString(70, y - 31, detail[:88])
                y -= 46
            if evaluation.get("evaluator_notes"):
                pdf.setFont("Helvetica-Oblique", 8.5)
                for line in _wrap_text(f"Notes: {evaluation['evaluator_notes']}", 96)[:2]:
                    pdf.drawString(64, y - 8, line)
                    y -= 12
            y -= 8
    else:
        pdf.setFont("Helvetica", 10)
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

    for evaluation in summary["rubric_evaluations"][:4]:
        score = _score_label(evaluation["total_points"], evaluation["max_points"])
        target = evaluation["assignment_title"] or evaluation["course_name"] or "General"
        draw.rounded_rectangle((50, y, 1150, y + 68), radius=10, fill="#fff8eb", outline="#d5c8aa")
        draw.text((70, y + 12), (evaluation["rubric_name"] or "Rubric")[:70], fill="#14213d", font=font_title)
        draw.text((930, y + 12), score, fill="#14213d", font=font_body)
        draw.text((70, y + 38), f"{evaluation['created_at'][:10]} - {target}"[:120], fill="#475569", font=font_body)
        y += 82
        for item in evaluation.get("items", [])[:5]:
            if y > 1430:
                break
            draw.rounded_rectangle((75, y, 1125, y + 58), radius=8, fill="#ffffff", outline="#d8d1c1")
            draw.text((95, y + 9), (item["criterion_title"] or "Criterion")[:45], fill="#1f2937", font=font_body)
            rating = item.get("rating_title") or ("Checked" if item.get("is_checked") else "No rating")
            draw.text((460, y + 9), rating[:44], fill="#1f2937", font=font_body)
            points = _score_label(item.get("points_awarded"), item.get("criterion_max_points"))
            draw.text((1010, y + 9), points, fill="#1f2937", font=font_body)
            detail = item.get("rating_description") or item.get("narrative_comment") or ""
            if detail:
                draw.text((95, y + 32), detail[:125], fill="#475569", font=font_body)
            y += 66

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
