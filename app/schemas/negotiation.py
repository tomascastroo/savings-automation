from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Literal
from datetime import datetime

class NegotiateRequest(BaseModel):
    target_pct: float = Field(default=0.2, ge=0, le=0.8)

class NegotiationRead(BaseModel):
    id: int
    status: str
    strategy: str
    initial_amount: float
    new_amount: float | None = None
    transcript_json: dict | None = None
    model_config = ConfigDict(from_attributes=True)

class ConfirmRequest(BaseModel):
    new_amount: float = Field(gt=0)
    valid_until: datetime | None = None
