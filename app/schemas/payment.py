from pydantic import BaseModel, Field, ConfigDict
from typing import Literal

class PaymentSetupRequest(BaseModel):
    provider: Literal["stripe","mp"] = "stripe"
    pm_token: str = Field(min_length=4)

class SavingRead(BaseModel):
    id: int
    saving_amount: float
    model_config = ConfigDict(from_attributes=True)

class FeeRead(BaseModel):
    id: int
    fee_amount: float
    payment_status: str
    model_config = ConfigDict(from_attributes=True)
