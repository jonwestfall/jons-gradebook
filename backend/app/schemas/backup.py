from pydantic import BaseModel


class BackupCreateRequest(BaseModel):
    note: str | None = None
