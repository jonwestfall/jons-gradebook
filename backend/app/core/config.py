import json
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = Field(default="Jon's Gradebook API", alias="APP_NAME")
    env: str = Field(default="development", alias="ENV")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    secret_key: str = Field(default="development-secret", alias="SECRET_KEY")
    encryption_key: str = Field(default="", alias="ENCRYPTION_KEY")

    database_url: str = Field(
        default="postgresql+psycopg://gradebook:gradebook@db:5432/gradebook",
        alias="DATABASE_URL",
    )

    canvas_base_url: str = Field(default="", alias="CANVAS_BASE_URL")
    canvas_api_token: str = Field(default="", alias="CANVAS_API_TOKEN")
    canvas_account_id: str = Field(default="", alias="CANVAS_ACCOUNT_ID")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")

    default_timezone: str = Field(default="America/Chicago", alias="DEFAULT_TIMEZONE")
    daily_sync_cron: str = Field(default="0 5 * * *", alias="DAILY_SYNC_CRON")

    storage_root: str = Field(default="/data/storage", alias="STORAGE_ROOT")
    backup_root: str = Field(default="/data/backups", alias="BACKUP_ROOT")

    cors_origins_raw: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    llm_deidentify_default: bool = Field(default=True, alias="LLM_DEIDENTIFY_DEFAULT")

    @property
    def cors_origins(self) -> list[str]:
        value = (self.cors_origins_raw or "").strip()
        if not value:
            return []

        if value.startswith("["):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
            except json.JSONDecodeError:
                pass

        return [origin.strip() for origin in value.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
