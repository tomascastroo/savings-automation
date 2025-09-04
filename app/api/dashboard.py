from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from ..dependencies import get_db, get_current_user
from ..models.payment import Saving, Fee, PaymentStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/me")
async def me(db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    total_saving = await db.scalar(select(func.coalesce(func.sum(Saving.saving_amount), 0)).where(Saving.user_id == user.id))
    fees_paid = await db.scalar(select(func.coalesce(func.sum(Fee.fee_amount), 0)).where(Fee.payment_status == PaymentStatus.paid))
    return {"total_saving": float(total_saving or 0), "fees_paid": float(fees_paid or 0)}
