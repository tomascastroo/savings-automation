from pydantic import BaseModel, Field, ConfigDict
from typing import Any
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

    # LLM preview fields
    llm_channel: str | None = None
    llm_message_preview: str | None = Field(None, max_length=160)
    llm_new_amount_suggestion: float | None = None
    llm_confidence: float | None = None

    model_config = ConfigDict(from_attributes=True)

class NegotiationMessageRead(BaseModel):
    channel: str
    subject: str | None
    message: str
    strategy: str
    new_amount_suggestion: float
    target_pct: float
    confidence: float
    risks: list[str]
    # meta field is intentionally not exposed here for security

    model_config = ConfigDict(from_attributes=True)

class RegenerateLlmMessageRequest(BaseModel):
    target_pct: float | None = Field(None, ge=0, le=0.8)
    channel: str | None = None
    context: dict | None = None

class ConfirmRequest(BaseModel):
    new_amount: float = Field(gt=0)
    valid_until: datetime | None = None
