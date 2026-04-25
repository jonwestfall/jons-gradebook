from pydantic import BaseModel, Field

from app.db.models import LLMProvider


class LLMPreviewRequest(BaseModel):
    provider: LLMProvider
    model: str
    prompt: str


class LLMOutputEditRequest(BaseModel):
    edited_text: str


class LLMInstructionTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    task_type: str = "feedback"
    instructions: str = Field(min_length=1)
    output_guidance: str | None = None
    rubric_guidance: str | None = None
    approval_status: str = "draft"
    approval_note: str | None = None
    policy_pack: str | None = None
    is_active: bool = True
    is_default: bool = False


class LLMInstructionTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    task_type: str | None = None
    instructions: str | None = Field(default=None, min_length=1)
    output_guidance: str | None = None
    rubric_guidance: str | None = None
    version: int | None = None
    approval_status: str | None = None
    approval_note: str | None = None
    policy_pack: str | None = None
    is_active: bool | None = None
    is_default: bool | None = None
    archived: bool | None = None


class LLMPasteOutputRequest(BaseModel):
    output_text: str = Field(min_length=1)


class LLMFinalFeedbackRequest(BaseModel):
    final_feedback: str = Field(min_length=1)


class LLMFinalizeRequest(BaseModel):
    title: str | None = None
