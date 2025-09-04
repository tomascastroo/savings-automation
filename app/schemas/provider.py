# app/schemas/provider.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional

class ProviderBase(BaseModel):
    name: str = Field(..., max_length=255)
    country: Optional[str] = Field(None, max_length=2)
    website: Optional[str] = Field(None, max_length=255)

class ProviderCreate(ProviderBase):
    pass

class ProviderUpdate(BaseModel):
    # All fields are optional for partial updates
    name: Optional[str] = Field(None, max_length=255)
    country: Optional[str] = Field(None, max_length=2)
    website: Optional[str] = Field(None, max_length=255)

    model_config = ConfigDict(extra='forbid')

class Provider(ProviderBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
