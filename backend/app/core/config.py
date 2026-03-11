from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "thesis-workflow-backend"
    app_env: str = "development"
    api_prefix: str = "/api"
    database_url: str = "postgresql+asyncpg://thesis:thesis@localhost:5432/thesis_workflow"
    redis_url: str = "redis://localhost:6379/0"
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "thesis-assets"
    websocket_channel: str = "tasks"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="THESIS_",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_non_dev_defaults(self) -> "Settings":
        insecure_database = "thesis:thesis@" in self.database_url
        insecure_minio = (
            self.minio_access_key == "minioadmin"
            or self.minio_secret_key == "minioadmin"
        )

        if self.app_env != "development" and (insecure_database or insecure_minio):
            raise ValueError("Non-development environments must override default local credentials")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
