# app/schemas/provider_plan.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, Dict, Any
from app.models.payment import ServiceCategory

class ProviderPlanBase(BaseModel):
    provider_id: int
    name: str = Field(..., max_length=255)
    category: ServiceCategory
    price: float
    currency: str = Field("ARS", max_length=3)
    details: Optional[Dict[str, Any]] = None
    active: bool = True

class ProviderPlanCreate(ProviderPlanBase):
    pass

class ProviderPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    category: Optional[ServiceCategory] = None
    price: Optional[float] = None
    currency: Optional[str] = Field(None, max_length=3)
    details: Optional[Dict[str, Any]] = None
    active: Optional[bool] = None

class ProviderPlan(ProviderPlanBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
