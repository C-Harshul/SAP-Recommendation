"""Environment and secrets configuration."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings from env (dev) or Secrets Manager (prod)."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = Field(default="dev", alias="EG_ENV")
    s3_bucket: str = Field(default="eg-lakehouse", alias="EG_S3_BUCKET")
    s3_bronze_prefix: str = Field(default="bronze", alias="EG_S3_BRONZE_PREFIX")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    aws_endpoint_url: str | None = Field(default=None, alias="AWS_ENDPOINT_URL")
    secrets_manager_secret_id: str | None = Field(default=None, alias="EG_SECRETS_ID")
    log_level: str = Field(default="INFO", alias="EG_LOG_LEVEL")
    health_port: int = Field(default=8080, alias="EG_HEALTH_PORT")

    # Per-source credentials (never in YAML)
    kaggle_username: str | None = Field(default=None, alias="KAGGLE_USERNAME")
    kaggle_key: str | None = Field(default=None, alias="KAGGLE_KEY")
    product_hunt_token: str | None = Field(default=None, alias="PRODUCT_HUNT_TOKEN")
    coursera_api_key: str | None = Field(default=None, alias="COURSERA_API_KEY")
    ideanote_api_key: str | None = Field(default=None, alias="IDEANOTE_API_KEY")
    udemy_affiliate_id: str | None = Field(default=None, alias="UDEMY_AFFILIATE_ID")

    def load_secrets_from_manager(self) -> None:
        """Overlay credentials from AWS Secrets Manager when EG_SECRETS_ID is set."""
        if not self.secrets_manager_secret_id:
            return
        import boto3

        client = boto3.client("secretsmanager", region_name=self.aws_region)
        resp = client.get_secret_value(SecretId=self.secrets_manager_secret_id)
        payload: dict[str, Any] = json.loads(resp["SecretString"])
        for key, value in payload.items():
            env_key = key.upper()
            if value and not os.environ.get(env_key):
                os.environ[env_key] = str(value)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.environment == "prod":
        settings.load_secrets_from_manager()
    return Settings()
