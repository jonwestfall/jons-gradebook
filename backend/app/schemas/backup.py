from pydantic import BaseModel


class BackupCreateRequest(BaseModel):
    note: str | None = None


class BackupRestoreRequest(BaseModel):
    backup_id: int
