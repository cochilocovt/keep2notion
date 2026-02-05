"""Shared configuration utilities."""

import os
from typing import Optional


def get_env(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """Get environment variable with optional default and required validation."""
    value = os.getenv(key, default)
    if required and not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


def get_database_url() -> str:
    """Get PostgreSQL database URL from environment."""
    return get_env(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/keep_notion_sync",
        required=False
    )


def get_aws_config() -> dict:
    """Get AWS configuration from environment."""
    return {
        "region": get_env("AWS_REGION", "us-east-1"),
        "s3_bucket": get_env("AWS_S3_BUCKET", "keep-notion-sync"),
        "access_key_id": get_env("AWS_ACCESS_KEY_ID"),
        "secret_access_key": get_env("AWS_SECRET_ACCESS_KEY"),
    }
