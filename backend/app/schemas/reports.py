from pydantic import BaseModel


class StudentReportRequest(BaseModel):
    include_all_rubrics: bool = True
    rubric_id: int | None = None
    assignment_id: int | None = None


class BulkStudentReportRequest(BaseModel):
    include_all_rubrics: bool = True
    rubric_id: int | None = None
    assignment_id: int | None = None
