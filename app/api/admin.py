from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from typing import List

from ..dependencies import get_db, require_admin
from ..models.provider import Provider
from ..schemas.provider import ProviderCreate, ProviderUpdate, Provider as ProviderSchema

router = APIRouter(prefix="/admin", tags=["admin"])

# --- Provider Management ---

@router.post("/providers/", response_model=ProviderSchema, status_code=status.HTTP_201_CREATED)
async def create_provider(
    provider_in: ProviderCreate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin)
):
    """
    Create a new provider. (Admin only)
    """
    # Check if provider already exists
    result = await db.execute(select(Provider).filter(Provider.name == provider_in.name))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Provider with this name already exists",
        )

    new_provider = Provider(**provider_in.model_dump())
    db.add(new_provider)
    await db.commit()
    await db.refresh(new_provider)
    return new_provider

@router.get("/providers/", response_model=List[ProviderSchema])
async def list_providers(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    _: str = Depends(require_admin)
):
    """
    List all providers. (Admin only)
    """
    result = await db.execute(select(Provider).offset(skip).limit(limit))
    return result.scalars().all()

@router.get("/providers/{provider_id}", response_model=ProviderSchema)
async def get_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin)
):
    """
    Get a single provider by ID. (Admin only)
    """
    provider = await db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
    return provider

@router.patch("/providers/{provider_id}", response_model=ProviderSchema)
async def update_provider(
    provider_id: int,
    provider_in: ProviderUpdate,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin)
):
    """
    Partially update a provider. (Admin only)
    """
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
async def delete_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(require_admin)
):
    """
    Delete a provider. (Admin only)
    """
    provider = await db.get(Provider, provider_id)
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    # Note: In a real world scenario, we should check for dependencies
    # (e.g., if any Service uses this provider) before deleting.
    await db.delete(provider)
    await db.commit()
    return None

# --- KPIs ---
# NOTE: The original KPI endpoint is preserved below.
from ..models.payment import Saving, Fee

@router.get("/kpis")
async def kpis(db: AsyncSession = Depends(get_db), _: str = Depends(require_admin)):
    total_saving = await db.scalar(select(func.coalesce(func.sum(Saving.saving_amount), 0)))
    total_fees = await db.scalar(select(func.coalesce(func.sum(Fee.fee_amount), 0)))
    return {"total_saving": float(total_saving or 0), "total_fees": float(total_fees or 0)}
