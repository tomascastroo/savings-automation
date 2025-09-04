# app/config.py
from __future__ import annotations
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List

class Settings(BaseSettings):
    # --- Core Infrastructure ---
    # These are required and must be set in the .env file
    database_url: str
    redis_url: str

    # --- Security ---
    # This is required and must be set in the .env file to a strong secret
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # This is parsed from a JSON string in the .env file.
    # e.g., ALLOWED_ORIGINS='["http://localhost:3000", "http://localhost:5173"]'
    # Defaults to ["*"] if not set, allowing all origins.
    allowed_origins: List[str] = Field(default=["*"])

    # --- Third-Party Services ---
    payment_gateway: str = Field(default="stripe", pattern="^(stripe|mp)$")
    openai_api_key: str | None = None

    # --- Application Settings ---
    storage_dir: str = Field(default="data")
    negotiation_rate_limit_days: int = 7
    success_fee_percentage: float = Field(default=0.20, ge=0, le=1.0)

    model_config = {
        "env_prefix": "",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

settings = Settings()