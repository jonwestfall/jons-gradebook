from pydantic import BaseModel

from app.db.models import LLMProvider


class LLMPreviewRequest(BaseModel):
    provider: LLMProvider
    model: str
    prompt: str


class LLMOutputEditRequest(BaseModel):
    edited_text: str
