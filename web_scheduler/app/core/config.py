from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    app_name: str = Field(default="web_scheduler", alias="APP_NAME")
    app_env: str = Field(default="local", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    database_url: str = Field(default="sqlite:///./web_scheduler.db", alias="DATABASE_URL")
    sql_runner_database_url: str | None = Field(default=None, alias="SQL_RUNNER_DATABASE_URL")
    sql_runner_allow_write: bool = Field(default=False, alias="SQL_RUNNER_ALLOW_WRITE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    default_timezone: str = Field(default="Asia/Seoul", alias="DEFAULT_TIMEZONE")
    cors_allow_origins: str = Field(default="http://localhost:5173,http://127.0.0.1:5173", alias="CORS_ALLOW_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_allow_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
