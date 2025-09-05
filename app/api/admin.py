from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import List

from ..dependencies import get_db, require_admin
from ..models.provider import Provider
from ..models.provider_plan import ProviderPlan
from ..models.negotiation import Negotiation
from ..models.payment import Fee, PaymentStatus, Saving, NegotiationStatus
from ..schemas.provider import ProviderCreate, ProviderUpdate, Provider as ProviderSchema
from ..schemas.provider_plan import ProviderPlanCreate, ProviderPlanUpdate, ProviderPlan as ProviderPlanSchema
from ..services.payment import refund_charge
from ..config import settings

router = APIRouter(prefix="/admin", tags=["admin"])

# --- LLM Status ---
class LlmStatusResponse(BaseModel):
    enabled: bool
    provider: str
    model: str
    dry_run: bool
    # In a real system, we'd add circuit breaker status, last error, etc.

@router.get("/llm/status", response_model=LlmStatusResponse)
async def get_llm_status(_: str = Depends(require_admin)):
    return {
        "enabled": settings.llm_enable,
        "provider": settings.llm_provider,
        "model": settings.llm_model,
        "dry_run": settings.llm_dry_run,
    }

# --- Provider Management ---

@router.post("/providers/", response_model=ProviderSchema, status_code=status.HTTP_201_CREATED)
async def create_provider(provider_in: ProviderCreate, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    result = await db.execute(select(Provider).filter(Provider.name == provider_in.name))
    if result.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Provider with this name already exists")
    new_provider = Provider(**provider_in.model_dump())
    db.add(new_provider)
    await db.commit()
    await db.refresh(new_provider)
    return new_provider

# ... (other provider endpoints are unchanged) ...
@router.get("/providers/", response_model=List[ProviderSchema])
async def list_providers(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 100, _: str = Depends(require_admin)):
    result = await db.execute(select(Provider).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/providers/{provider_id}", response_model=ProviderSchema)
async def get_provider(provider_id: int, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    provider = await db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return provider

@router.patch("/providers/{provider_id}", response_model=ProviderSchema)
async def update_provider(provider_id: int, provider_in: ProviderUpdate, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    provider = await db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    update_data = provider_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(provider, key, value)
    await db.commit()
    await db.refresh(provider)
    return provider

@router.delete("/providers/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(provider_id: int, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    provider = await db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    await db.delete(provider)
    await db.commit()
    return None

# --- Plan Management ---

@router.post("/plans/", response_model=ProviderPlanSchema, status_code=status.HTTP_201_CREATED)
async def create_provider_plan(plan_in: ProviderPlanCreate, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    new_plan = ProviderPlan(**plan_in.model_dump())
    db.add(new_plan)
    await db.commit()
    await db.refresh(new_plan)
    return new_plan

@router.get("/plans/", response_model=List[ProviderPlanSchema])
async def list_provider_plans(db: AsyncSession = Depends(get_db), skip: int = 0, limit: int = 100, _: str = Depends(require_admin)):
    result = await db.execute(select(ProviderPlan).offset(skip).limit(limit))
    return result.scalars().all()

# --- Payment Management ---

class RefundRequest(BaseModel):
    fee_id: int
    reason: str

@router.post("/refunds/", status_code=status.HTTP_200_OK)
async def process_refund(refund_in: RefundRequest, db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    fee = await db.get(Fee, refund_in.fee_id)
    if not fee:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fee not found")
    if fee.payment_status != PaymentStatus.paid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Fee is not in a refundable state.")
    refund_result = await refund_charge(fee=fee, reason=refund_in.reason)
    if not refund_result.success:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Refund failed: {refund_result.error}")
    fee.payment_status = PaymentStatus.refunded
    fee.payment_ref = refund_result.reference
    await db.commit()
    await db.refresh(fee)
    return {"status": "refunded", "fee_id": fee.id, "new_payment_ref": refund_result.reference}

# --- KPIs ---

@router.get("/kpis")
async def kpis(db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    total_saving = await db.scalar(select(func.coalesce(func.sum(Saving.saving_amount), 0)))
    total_fees = await db.scalar(select(func.coalesce(func.sum(Fee.fee_amount), 0)))
    successful_negotiations = await db.scalar(select(func.count()).where(Negotiation.status == NegotiationStatus.accepted))

    return {
        "total_saving_achieved": float(total_saving or 0),
        "total_fees_collected": float(total_fees or 0),
        "successful_negotiations": successful_negotiations or 0
    }
