"""Central application configuration (environment-based)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_secret_key: str = Field(default="dev-secret-change-me", alias="APP_SECRET_KEY")
    backend_port: int = Field(default=8000, alias="BACKEND_PORT")

    database_url: str = Field(default="sqlite:///./data/reframe.db", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    model_api_key: str = Field(default="", alias="MODEL_API_KEY")
    model_api_base: str = Field(default="https://api.meta.ai/v1", alias="MODEL_API_BASE")
    sam_model: str = Field(default="sam-3.1", alias="SAM_MODEL")
    spark_model: str = Field(default="muse-spark-1.3", alias="SPARK_MODEL")
    image_model: str = Field(default="muse-image-1.0", alias="IMAGE_MODEL")

    s3_endpoint: str = Field(default="", alias="S3_ENDPOINT")
    s3_bucket: str = Field(default="reframeai", alias="S3_BUCKET")
    s3_access_key: str = Field(default="", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="", alias="S3_SECRET_KEY")
    s3_region: str = Field(default="us-east-1", alias="S3_REGION")

    storage_dir: str = Field(default="./data/storage", alias="STORAGE_DIR")
    max_upload_mb: int = Field(default=500, alias="MAX_UPLOAD_MB")
    max_duration_sec: int = Field(default=600, alias="MAX_DURATION_SEC")

    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def ai_configured(self) -> bool:
        return bool(self.model_api_key.strip())

    @property
    def s3_configured(self) -> bool:
        return bool(self.s3_endpoint.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
