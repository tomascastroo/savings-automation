# app/tests/_helpers.py
import io
from uuid import uuid4
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.provider import Provider
from app.models.payment import Service, ServiceCategory

from typing import Optional, Dict, Any

async def ensure_provider_and_service(
    db: AsyncSession,
    user_id: int,
    provider_kwargs: Optional[Dict[str, Any]] = None
) -> tuple[int, int]:
    """
    Ensures a provider and a unique service for that user exist,
    using the provided test database session.
    """
    provider_kwargs = provider_kwargs or {}
    provider_name = provider_kwargs.get("name", "TelecomX")

    # Reuse provider by name
    p = await db.scalar(select(Provider).where(Provider.name == provider_name))
    if not p:
        # Provide default values and override with any kwargs
        defaults = {"name": "TelecomX", "country": "AR", "website": "https://telecomx.example"}
        p = Provider(**{**defaults, **provider_kwargs})
        db.add(p)
        await db.flush()

    # Always create a new Service with a unique provider_acct to avoid rate limit collisions
    acct = f"ACC{uuid4().hex[:10]}"
    s = Service(
        user_id=user_id,
        provider_id=p.id,
        category=ServiceCategory.internet,
        provider_acct=acct,
        alias=f"TelecomX {acct[-4:]}",
        active=True,
    )
    db.add(s)
    await db.flush()
    # The calling test is responsible for the commit
    return p.id, s.id


def make_dummy_image_bytes() -> bytes:
    img = Image.new("RGB", (2, 2), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()