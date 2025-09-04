# app/config.py
from __future__ import annotations
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Any
import json
import os

class Settings(BaseSettings):
    database_url: str = Field(default="postgresql+asyncpg://savings:savings@db:5432/savings")
    redis_url: str = Field(default="redis://redis:6379/0")
    jwt_secret: str = Field(default="change-me")
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=60)

    # Leemos el env como STRING para esquivar el json.loads automático de pydantic-settings
    allowed_origins_env: str | None = Field(default=None, alias="ALLOWED_ORIGINS")

    payment_gateway: str = Field(default="stripe")  # stripe|mp
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    storage_dir: str = Field(default="/data")
    negotiation_rate_limit_days: int = Field(default=7)
    success_fee_percentage: float = Field(default=0.2)

    model_config = {
        "env_prefix": "",
        "env_file": ".env",
        "populate_by_name": True,
    }

    @property
    def allowed_origins(self) -> list[str]:
        """
        Normaliza orígenes CORS desde:
        - JSON: '["http://localhost:3000","http://localhost:5173"]'
        - CSV:  'http://localhost:3000,http://localhost:5173'
        - vacío/None -> ["*"]
        """
        raw = self.allowed_origins_env or os.getenv("ALLOWED_ORIGINS") or ""
        raw = raw.strip()
        if not raw:
            return ["*"]
        if raw.startswith("[") and raw.endswith("]"):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list) and all(isinstance(x, str) for x in parsed):
                    return parsed
            except Exception:
                pass
        # CSV
        return [x.strip() for x in raw.split(",") if x.strip()]

settings = Settings()