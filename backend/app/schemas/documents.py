from pydantic import BaseModel


class DocumentUploadMetadata(BaseModel):
    owner_type: str
    owner_id: int
    title: str
    document_id: int | None = None
