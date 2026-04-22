from pydantic import BaseModel

from app.db.models import SyncTrigger


class CanvasSyncRequest(BaseModel):
    trigger_type: SyncTrigger = SyncTrigger.manual
    snapshot_label: str | None = None
    canvas_course_ids: list[str] | None = None


class CanvasCourseSelectionUpdateRequest(BaseModel):
    canvas_course_ids: list[str]
    mode: str = "replace"


class CanvasStudentFieldMappingUpdateRequest(BaseModel):
    target_field: str
    source_paths: list[str]
