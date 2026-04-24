from typing import Any

from pydantic import BaseModel, Field


class ReportTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    config_json: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False


class ReportTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    config_json: dict[str, Any] | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    archived: bool | None = None


class StudentReportRequest(BaseModel):
    template_id: int | None = None
    include_all_rubrics: bool = True
    rubric_id: int | None = None
    assignment_id: int | None = None


class BulkStudentReportRequest(BaseModel):
    template_id: int | None = None
    include_all_rubrics: bool = True
    rubric_id: int | None = None
    assignment_id: int | None = None
