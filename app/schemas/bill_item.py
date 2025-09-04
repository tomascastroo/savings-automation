# app/schemas/bill_item.py
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional

class BillItemBase(BaseModel):
    bill_id: int
    description: str = Field(..., max_length=255)
    amount: float
    quantity: Optional[float] = None
    unit_price: Optional[float] = None

class BillItemCreate(BillItemBase):
    pass

class BillItem(BillItemBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
