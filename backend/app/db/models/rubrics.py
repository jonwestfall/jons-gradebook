from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.common import Base, TimestampMixin


class RubricCriterionType(str, enum.Enum):
    points = "points"
    checkbox = "checkbox"
    narrative = "narrative"


class RubricTemplate(Base, TimestampMixin):
    __tablename__ = "rubric_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    max_points: Mapped[Optional[float]] = mapped_column(Float)

    criteria = relationship("RubricCriterion", back_populates="rubric", cascade="all, delete-orphan")


class RubricCriterion(Base, TimestampMixin):
    __tablename__ = "rubric_criteria"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rubric_id: Mapped[int] = mapped_column(ForeignKey("rubric_templates.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    criterion_type: Mapped[RubricCriterionType] = mapped_column(Enum(RubricCriterionType), nullable=False)
    max_points: Mapped[Optional[float]] = mapped_column(Float)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prompt: Mapped[Optional[str]] = mapped_column(Text)

    rubric = relationship("RubricTemplate", back_populates="criteria")


class RubricEvaluation(Base, TimestampMixin):
    __tablename__ = "rubric_evaluations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    rubric_id: Mapped[int] = mapped_column(ForeignKey("rubric_templates.id", ondelete="CASCADE"), nullable=False)
    student_profile_id: Mapped[Optional[int]] = mapped_column(ForeignKey("student_profiles.id", ondelete="SET NULL"))
    course_id: Mapped[Optional[int]] = mapped_column(ForeignKey("courses.id", ondelete="SET NULL"))
    assignment_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assignments.id", ondelete="SET NULL"))
    evaluator_notes: Mapped[Optional[str]] = mapped_column(Text)
    total_points: Mapped[Optional[float]] = mapped_column(Float)

    items = relationship("RubricEvaluationItem", back_populates="evaluation", cascade="all, delete-orphan")


class RubricEvaluationItem(Base, TimestampMixin):
    __tablename__ = "rubric_evaluation_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("rubric_evaluations.id", ondelete="CASCADE"), nullable=False)
    criterion_id: Mapped[int] = mapped_column(ForeignKey("rubric_criteria.id", ondelete="CASCADE"), nullable=False)
    points_awarded: Mapped[Optional[float]] = mapped_column(Float)
    is_checked: Mapped[Optional[bool]] = mapped_column(Boolean)
    narrative_comment: Mapped[Optional[str]] = mapped_column(Text)

    evaluation = relationship("RubricEvaluation", back_populates="items")
