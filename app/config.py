from typing import Set, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "application/pdf",
    "text/plain",
    "text/csv",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/zip",
    "application/x-gzip",
    "application/x-rar-compressed",
}


class Settings(BaseSettings):
    upload_dir: str = "./uploads"
    max_file_size: int = 10 * 1024 * 1024
    allowed_content_types: Optional[Set[str]] = None

    @property
    def effective_allowed_content_types(self) -> Set[str]:
        if self.allowed_content_types is not None:
            return self.allowed_content_types
        return DEFAULT_ALLOWED_CONTENT_TYPES

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()