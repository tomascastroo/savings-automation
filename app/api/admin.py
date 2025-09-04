from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from ..dependencies import get_db, require_admin
from ..models.payment import Saving, Fee

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/kpis")
async def kpis(db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    total_saving = await db.scalar(select(func.coalesce(func.sum(Saving.saving_amount), 0)))
    total_fees = await db.scalar(select(func.coalesce(func.sum(Fee.fee_amount), 0)))
    return {"total_saving": float(total_saving or 0), "total_fees": float(total_fees or 0)}
