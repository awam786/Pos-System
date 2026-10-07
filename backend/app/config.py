from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central application configuration.

    Every production-sensitive value is loaded from environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Professional General Store POS"
    app_env: str = "production"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/pos"
    )

    # Security
    secret_key: str = "CHANGE_ME"
    access_token_expire_minutes: int = 720

    # Initial shop
    initial_shop_name: str = "General Store"
    initial_shop_address: str = ""
    initial_shop_phone: str = ""
    initial_shop_email: str = ""

    # Initial owner
    initial_owner_username: str = "admin"
    initial_owner_password: str = "CHANGE_ME"
    initial_owner_name: str = "Store Owner"
    initial_owner_email: str = ""

    # Business
    default_currency: str = "PKR"
    default_timezone: str = "Asia/Karachi"

    # Receipts
    default_receipt_width: int = 80
    default_receipt_footer: str = "Thank you for shopping with us!"

    # CORS
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # Uploads
    max_upload_size_mb: int = 5

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [
                origin.strip()
                for origin in value.split(",")
                if origin.strip()
            ]

        if isinstance(value, list):
            return value

        return []

    @field_validator("default_receipt_width")
    @classmethod
    def validate_receipt_width(cls, value: int) -> int:
        if value not in (58, 80):
            raise ValueError("Receipt width must be either 58 or 80.")
        return value

    @field_validator("max_upload_size_mb")
    @classmethod
    def validate_upload_size(cls, value: int) -> int:
        if value < 1 or value > 25:
            raise ValueError("Maximum upload size must be between 1 and 25 MB.")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
