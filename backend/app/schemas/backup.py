from pydantic import BaseModel


class BackupCreateRequest(BaseModel):
    note: str | None = None


class BackupRestoreRequest(BaseModel):
    backup_id: int
    # Take an automatic backup of the current state first, so a restore can be undone.
    create_safety_backup: bool = True
