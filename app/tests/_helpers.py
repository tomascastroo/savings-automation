# app/tests/_helpers.py
import io
from uuid import uuid4
from PIL import Image
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.provider import Provider
from app.models.payment import Service, ServiceCategory

async def ensure_provider_and_service(user_id: int) -> tuple[int, int]:
    async with AsyncSessionLocal() as db:
        # Reusar proveedor por nombre
        p = await db.scalar(select(Provider).where(Provider.name == "TelecomX"))
        if not p:
            p = Provider(name="TelecomX", country="AR", website="https://telecomx.example")
            db.add(p)
            await db.flush()

        # Siempre crear un Service nuevo con provider_acct único para evitar colisiones de rate limit
        acct = f"ACC{uuid4().hex[:10]}"
        s = Service(
            user_id=user_id,
            provider_id=p.id,
            category=ServiceCategory.internet,  # NOT NULL
            provider_acct=acct,                 # NOT NULL y único por prueba
            alias=f"TelecomX {acct[-4:]}",
            # active=True,  # si tu modelo no tiene default, descomenta
        )
        db.add(s)
        await db.flush()
        await db.commit()
        return p.id, s.id


def make_dummy_image_bytes() -> bytes:
    img = Image.new("RGB", (2, 2), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()