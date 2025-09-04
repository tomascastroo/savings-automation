from pydantic import BaseModel, Field, ConfigDict
from typing import Any

class BillCreate(BaseModel):
    service_id: int
    period_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    amount_due: float = Field(gt=0)
    currency: str = "ARS"

class BillRead(BaseModel):
    id: int
    service_id: int
    period_month: str
    amount_due: float
    currency: str
    ocr_json: dict | None = None
    model_config = ConfigDict(from_attributes=True)
